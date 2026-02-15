"""Gemini LLM client implementation."""

import asyncio
import functools
import logging
import time
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from courseflow.domain.exceptions import (
    QuotaExceededError,
    ServiceUnavailableError,
)
from courseflow.domain.models import TokenUsage
from courseflow.domain.ports import LLMPort

logger = logging.getLogger(__name__)


class GeminiLLMClient(LLMPort):
    """Gemini LLM client with retry logic and error handling.

    Implements LLMPort interface for generating answers using Google's Gemini API.
    Includes exponential backoff retry logic for transient failures.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        """Initialize Gemini LLM client.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use (default: gemini-2.5-flash-lite)
            max_retries: Maximum retry attempts for transient failures
            timeout_seconds: Request timeout in seconds
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._did_model_fallback = False

        # Initialize Google GenAI client
        self.client = genai.Client(api_key=api_key)

        logger.info(f"Initialized Gemini LLM client with model: {model_name}")

    async def generate_answer(
        self,
        query: str,
        context: list[str],
    ) -> tuple[str, TokenUsage]:
        """Generate answer using Gemini LLM with retry logic.

        Args:
            query: User's question
            context: List of relevant document excerpts for RAG

        Returns:
            Tuple of (answer_text, token_usage)

        Raises:
            QuotaExceededError: When API quota is exceeded
            ServiceUnavailableError: When service is unavailable after retries
        """
        # Construct prompt
        prompt = self._build_prompt(query, context)

        # Generate with retry logic
        try:
            response = await self._generate_with_retry(prompt)
        except Exception as e:
            if (not self._did_model_fallback) and self._is_model_not_found_error(e):
                fallback = self._select_fallback_model_name()
                if fallback:
                    self._did_model_fallback = True
                    logger.warning(
                        f"Gemini model '{self.model_name}' unavailable; falling back to '{fallback}'."
                    )
                    self.model_name = fallback
                    response = await self._generate_with_retry(prompt)
                else:
                    logger.error(f"Failed to generate answer: {e}")
                    raise
            else:
                logger.error(f"Failed to generate answer: {e}")
                raise

        # Extract answer text
        answer_text = (response.text or "").strip()
        if not answer_text:
            raise ServiceUnavailableError("Gemini API returned empty response")

        # Extract token usage
        token_usage = self._extract_token_usage(response)

        logger.info(
            f"Generated answer: {len(answer_text)} chars, {token_usage.total_tokens} tokens"
        )

        return answer_text, token_usage

    async def stream(
        self,
        query: str,
        context: list[str],
    ) -> AsyncGenerator[str, None]:
        """Stream answer chunks from Gemini LLM.

        Args:
            query: User's question
            context: List of relevant document excerpts for RAG

        Yields:
            Text chunks as they arrive from Gemini API

        Raises:
            QuotaExceededError: When API quota is exceeded
            ServiceUnavailableError: When service is unavailable
        """
        # Construct prompt
        prompt = self._build_prompt(query, context)

        logger.info(f"Starting streaming response for query: {query[:50]}...")

        try:
            # Call Gemini streaming API
            response = self._stream_with_retry(prompt)

            # Iterate through chunks
            token_count = 0
            async for chunk in response:
                # Extract text from chunk
                if hasattr(chunk, "text") and chunk.text:
                    text = chunk.text
                    token_count += len(text.split())
                    yield text
                    logger.debug(f"Streamed chunk: {len(text)} chars")

            logger.info(f"Streaming complete: ~{token_count} tokens")

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.error(f"Rate limit exceeded during streaming: {e}")
                raise QuotaExceededError(
                    message=f"Gemini API quota exceeded during streaming: {e}",
                    retry_after=60,
                ) from e
            elif "503" in error_msg or "unavailable" in error_msg.lower():
                logger.error(f"Service unavailable during streaming: {e}")
                raise ServiceUnavailableError(
                    message="Gemini API unavailable during streaming"
                ) from e
            else:
                logger.error(f"Streaming error: {e}")
                raise

    def _build_prompt(self, query: str, context: list[str]) -> str:
        """Build RAG prompt from query and context documents.

        Args:
            query: User's question
            context: List of relevant document excerpts

        Returns:
            Formatted prompt string
        """
        # Combine context documents
        context_text = "\n\n".join([f"Document {i + 1}:\n{doc}" for i, doc in enumerate(context)])

        # Build prompt with instruction, context, and query
        prompt = f"""You are a helpful educational assistant. Answer the student's question using ONLY the information provided in the context documents below. If the answer cannot be found in the context, say so explicitly.

Context Documents:
{context_text}

Student Question: {query}

Answer (be concise and factual, citing specific information from the documents):"""

        return prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def _generate_with_retry(
        self,
        prompt: str,
    ) -> types.GenerateContentResponse:
        """Generate content with exponential backoff retry.

        Args:
            prompt: Formatted prompt text

        Returns:
            Gemini API response

        Raises:
            QuotaExceededError: When rate limit is exceeded
            ServiceUnavailableError: When service is unavailable
            asyncio.TimeoutError: When request times out
        """
        try:
            start_time = time.time()

            # Run synchronous Gemini API in executor
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                    ),
                ),
                timeout=self.timeout_seconds,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"LLM generation took {elapsed_ms}ms")

            return response

        except TimeoutError:
            logger.warning(f"LLM request timed out after {self.timeout_seconds}s")
            raise

        except Exception as e:
            # Categorize errors
            error_str = str(e).lower()

            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                # Extract retry_after from error if available
                retry_after = 60  # Default to 1 minute
                logger.warning(f"Gemini API quota exceeded: {e}")
                raise QuotaExceededError(
                    message=f"Gemini API quota exceeded: {e}",
                    retry_after=retry_after,
                ) from e

            elif "503" in error_str or "unavailable" in error_str:
                logger.error(f"Gemini API unavailable: {e}")
                raise ServiceUnavailableError(
                    message="Gemini API is temporarily unavailable"
                ) from e

            else:
                logger.error(f"Unexpected Gemini API error: {e}")
                raise ServiceUnavailableError(message=f"Failed to generate answer: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def _stream_with_retry(
        self,
        prompt: str,
    ) -> AsyncGenerator[types.GenerateContentResponse, None]:
        """Stream content with exponential backoff retry.

        Args:
            prompt: Formatted prompt text

        Yields:
            Gemini API response chunks

        Raises:
            QuotaExceededError: When rate limit is exceeded
            ServiceUnavailableError: When service is unavailable
            asyncio.TimeoutError: When request times out
        """
        try:
            start_time = time.time()

            # Call streaming API
            loop = asyncio.get_running_loop()

            # Run synchronous streaming API in executor
            response_iter = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(
                        self.client.models.generate_content_stream,
                        model=self.model_name,
                        contents=prompt,
                    ),
                ),
                timeout=self.timeout_seconds,
            )

            logger.debug("Started streaming response")

            # Yield chunks from iterator
            for response_chunk in response_iter:
                elapsed_ms = int((time.time() - start_time) * 1000)
                if elapsed_ms > self.timeout_seconds * 1000:
                    raise TimeoutError(f"Streaming exceeded {self.timeout_seconds}s timeout")
                yield response_chunk

        except TimeoutError:
            logger.warning(f"LLM streaming timed out after {self.timeout_seconds}s")
            raise

        except Exception as e:
            # Categorize errors
            error_str = str(e).lower()

            if "quota" in error_str or "rate limit" in error_str or "429" in error_str:
                retry_after = 60
                logger.warning(f"Gemini API quota exceeded during streaming: {e}")
                raise QuotaExceededError(
                    message=f"Gemini API quota exceeded during streaming: {e}",
                    retry_after=retry_after,
                ) from e

            elif "503" in error_str or "unavailable" in error_str:
                logger.error(f"Gemini API unavailable during streaming: {e}")
                raise ServiceUnavailableError(
                    message="Gemini API is temporarily unavailable"
                ) from e

            else:
                logger.error(f"Unexpected Gemini API error during streaming: {e}")
                raise ServiceUnavailableError(message=f"Failed to stream answer: {str(e)}") from e

    def _is_model_not_found_error(self, exc: Exception) -> bool:
        msg = str(exc)
        lower = msg.lower()
        return (
            "404" in lower
            and ("not found" in lower or "is not found" in lower)
            and "model" in lower
        ) or ("not supported for generatecontent" in lower)

    def _select_fallback_model_name(self) -> str | None:
        try:
            models = list(self.client.models.list())
        except Exception as e:
            logger.warning(f"Failed to list Gemini models for fallback selection: {e}")
            return None

        generation_models = [
            m
            for m in models
            if isinstance(getattr(m, "name", None), str)
            and any(
                action in {"generatecontent", "generate_content"}
                for action in [
                    str(a).lower()
                    for a in getattr(m, "supported_actions", [])
                    if isinstance(a, str)
                ]
            )
        ]
        if not generation_models:
            return None

        available = {
            m.name.removeprefix("models/") for m in generation_models if isinstance(m.name, str)
        }
        preferred = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
        ]
        for name in preferred:
            if name in available:
                return name

        return sorted(available)[0]

    def _extract_token_usage(
        self,
        response: types.GenerateContentResponse,
    ) -> TokenUsage:
        """Extract token usage from Gemini response.

        Args:
            response: Gemini API response

        Returns:
            TokenUsage model with prompt, completion, and total tokens
        """
        try:
            # Gemini provides usage metadata
            usage = response.usage_metadata
            if usage is None:
                raise AttributeError("usage_metadata is missing")

            return TokenUsage(
                prompt_tokens=usage.prompt_token_count or 0,
                completion_tokens=usage.candidates_token_count or 0,
                total_tokens=usage.total_token_count or 0,
            )
        except (AttributeError, KeyError) as e:
            logger.warning(f"Failed to extract token usage: {e}")
            # Return default if usage metadata unavailable
            return TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )
