"""
Port interface for Wikipedia content scraping.

This port abstracts the Wikipedia data source, allowing different
implementations (MediaWiki API, Wikipedia dumps, mock for testing).

Part of hexagonal architecture: Domain layer depends on this interface,
infrastructure layer provides concrete implementations.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol


class WikipediaArticle(Protocol):
    """
    Article retrieved from Wikipedia.
    
    This is a protocol (structural subtyping) rather than inheritance-based,
    allowing any object with these attributes to satisfy the contract.
    """
    title: str
    canonical_title: str
    source_url: str
    content: str
    retrieved_at: datetime
    word_count: int
    api_response_metadata: dict


class ScrapingPort(ABC):
    """
    Interface for retrieving Wikipedia content.
    
    Implementations must handle rate limiting, retries, and error handling
    internally according to configuration. Domain logic should not concern
    itself with these infrastructure details.
    
    Example implementations:
    - MediaWikiAdapter: Real API calls to Wikipedia
    - MockScrapingAdapter: In-memory mock for testing
    - WikipediaDumpAdapter: Read from XML dump files (future)
    """
    
    @abstractmethod
    async def fetch_article(self, title: str) -> WikipediaArticle:
        """
        Fetch a single Wikipedia article by title.
        
        Handles redirects transparently - returned article.canonical_title
        may differ from input title if article was redirected.
        
        Respects rate limiting configured in the adapter. Caller does not
        need to implement rate limiting logic.
        
        Args:
            title: Wikipedia article title (e.g., "Python (programming language)").
                   Case-sensitive. Spaces allowed.
        
        Returns:
            WikipediaArticle with content and metadata.
        
        Raises:
            ArticleNotFoundError: Article does not exist (404 from Wikipedia).
                                  This is a permanent failure - do not retry.
            
            RateLimitError: Rate limit exceeded even after retries (429 from Wikipedia).
                           Adapter has exhausted retry attempts. Caller should
                           stop scraping or wait longer.
            
            NetworkError: Connection failure or timeout after retries.
                         May be transient (network down) or permanent (DNS failure).
            
            ParsingError: Failed to parse MediaWiki API response.
                         Indicates unexpected API response structure.
                         This is a bug or API version incompatibility.
        
        Example:
            ```python
            article = await scraping_port.fetch_article("Python (programming language)")
            print(article.canonical_title)  # "Python (programming language)"
            print(article.word_count)       # 15234
            ```
        """
        pass
    
    @abstractmethod
    async def validate_article_exists(self, title: str) -> bool:
        """
        Check if article exists without retrieving full content.
        
        Used for dry-run mode validation and existence checks before
        expensive full fetch operations.
        
        Does NOT follow redirects - checks if the exact title exists.
        Use follow_redirect() first if you need canonical title.
        
        Args:
            title: Wikipedia article title to check.
        
        Returns:
            True if article exists, False if 404 or does not exist.
            Returns False for network errors (fail-safe behavior).
        
        Example:
            ```python
            exists = await scraping_port.validate_article_exists("Python (programming language)")
            if not exists:
                print("Article not found")
            ```
        """
        pass
    
    @abstractmethod
    async def follow_redirect(self, title: str) -> str:
        """
        Resolve redirects to get canonical article title.
        
        Wikipedia articles can redirect to other articles.
        Example: "Python programming" → "Python (programming language)"
        
        This method follows the redirect chain and returns the final
        canonical title without fetching full article content.
        
        Args:
            title: Wikipedia article title (may be redirect).
        
        Returns:
            Canonical title after following redirects.
            If title is not a redirect, returns title unchanged.
        
        Raises:
            ArticleNotFoundError: Article does not exist (404).
            NetworkError: Connection failure or timeout.
        
        Example:
            ```python
            canonical = await scraping_port.follow_redirect("Python programming")
            print(canonical)  # "Python (programming language)"
            ```
        """
        pass
