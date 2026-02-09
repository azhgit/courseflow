"""Gemini embedding client implementing EmbeddingPort.

This module provides async embedding generation using Google's Gemini API.
Implements retry logic and error categorization for production use.
"""

import asyncio
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from courseflow.config import settings
from courseflow.domain.exceptions import (
    QuotaExceededError,
    ServiceUnavailableError,
    TimeoutError as CourseFlowTimeoutError
)
from courseflow.domain.ports import EmbeddingPort


class GeminiEmbeddingClient(EmbeddingPort):
    """Gemini API client for generating text embeddings.
    
    Uses the text-embedding-004 model to generate 768-dimensional embeddings.
    Implements exponential backoff retry for transient failures.
    
    Attributes:
        api_key: Google Gemini API key
        base_url: Gemini API base URL
        model: Embedding model name
        client: Async HTTP client
    """
    
    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001"):
        """Initialize Gemini embedding client.
        
        Args:
            api_key: Google Gemini API key
            model: Embedding model name (default: models/gemini-embedding-001)
        """
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = model
        self.client = httpx.AsyncClient(
            timeout=settings.EMBEDDING_TIMEOUT_SECONDS,
            headers={"x-goog-api-key": api_key}
        )
    
    async def close(self) -> None:
        """Close the HTTP client. Call this when shutting down."""
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def generate_embedding(
        self,
        text: str,
        timeout: int = 10
    ) -> list[float]:
        """Generate embedding vector for text.
        
        Implements exponential backoff retry (1s, 2s, 4s) for transient failures.
        
        Args:
            text: Input text to embed
            timeout: Maximum time to wait for response (seconds)
        
        Returns:
            768-dimensional embedding vector
        
        Raises:
            QuotaExceededError: If API quota is exceeded (429)
            CourseFlowTimeoutError: If request times out
            ServiceUnavailableError: If Gemini API is unreachable (5xx)
        """
        url = f"{self.base_url}/{self.model}:embedContent"
        payload = {
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                timeout=timeout
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                raise QuotaExceededError(
                    "Gemini API quota exceeded (15 RPM limit)",
                    retry_after=60  # Estimate 60s for RPM reset
                )
            
            # Check for service errors
            if response.status_code >= 500:
                raise ServiceUnavailableError(
                    f"Gemini API temporarily unavailable (status {response.status_code})"
                )
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Extract embedding from response
            data = response.json()
            embedding = data["embedding"]["values"]
            
            return embedding
            
        except httpx.TimeoutException as e:
            raise CourseFlowTimeoutError(
                f"Embedding generation timed out after {timeout}s"
            ) from e
        except httpx.RequestError as e:
            raise ServiceUnavailableError(
                f"Failed to connect to Gemini API: {str(e)}"
            ) from e
        except KeyError as e:
            raise ServiceUnavailableError(
                f"Unexpected response format from Gemini API: {str(e)}"
            ) from e
