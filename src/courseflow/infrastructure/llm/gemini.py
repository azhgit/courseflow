"""Gemini LLM client implementation."""

import asyncio
import logging
from typing import Tuple, List
import time

import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.courseflow.domain.ports import LLMPort
from src.courseflow.domain.models import TokenUsage
from src.courseflow.domain.exceptions import (
    QuotaExceededError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class GeminiLLMClient(LLMPort):
    """Gemini LLM client with retry logic and error handling.
    
    Implements LLMPort interface for generating answers using Google's Gemini API.
    Includes exponential backoff retry logic for transient failures.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash",
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        """Initialize Gemini LLM client.
        
        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use (default: gemini-1.5-flash)
            max_retries: Maximum retry attempts for transient failures
            timeout_seconds: Request timeout in seconds
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        logger.info(f"Initialized Gemini LLM client with model: {model_name}")

    async def generate_answer(
        self,
        query: str,
        context: List[str],
    ) -> Tuple[str, TokenUsage]:
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
            
            # Extract answer text
            answer_text = response.text.strip()
            
            # Extract token usage
            token_usage = self._extract_token_usage(response)
            
            logger.info(
                f"Generated answer: {len(answer_text)} chars, "
                f"{token_usage.total_tokens} tokens"
            )
            
            return answer_text, token_usage
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise

    def _build_prompt(self, query: str, context: List[str]) -> str:
        """Build RAG prompt from query and context documents.
        
        Args:
            query: User's question
            context: List of relevant document excerpts
            
        Returns:
            Formatted prompt string
        """
        # Combine context documents
        context_text = "\n\n".join([
            f"Document {i+1}:\n{doc}"
            for i, doc in enumerate(context)
        ])
        
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
    ) -> GenerateContentResponse:
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
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self.model.generate_content,
                    prompt,
                ),
                timeout=self.timeout_seconds,
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"LLM generation took {elapsed_ms}ms")
            
            return response
            
        except asyncio.TimeoutError:
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
                    message="Gemini API quota exceeded (15 RPM limit)",
                    retry_after=retry_after,
                )
            
            elif "503" in error_str or "unavailable" in error_str:
                logger.error(f"Gemini API unavailable: {e}")
                raise ServiceUnavailableError(
                    message="Gemini API is temporarily unavailable"
                )
            
            else:
                logger.error(f"Unexpected Gemini API error: {e}")
                raise ServiceUnavailableError(
                    message=f"Failed to generate answer: {str(e)}"
                )

    def _extract_token_usage(
        self,
        response: GenerateContentResponse,
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
            
            return TokenUsage(
                prompt_tokens=usage.prompt_token_count,
                completion_tokens=usage.candidates_token_count,
                total_tokens=usage.total_token_count,
            )
        except (AttributeError, KeyError) as e:
            logger.warning(f"Failed to extract token usage: {e}")
            # Return default if usage metadata unavailable
            return TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )
