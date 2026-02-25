"""
Port interface for content processing operations.

This port abstracts content transformation logic (parsing MediaWiki API
responses, chunking text with sentence boundaries, validation) to keep
domain logic separate from NLP/parsing implementation details.

Part of hexagonal architecture: Domain layer depends on this interface,
infrastructure layer provides concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Protocol


class WikipediaArticle(Protocol):
    """Article retrieved from Wikipedia (see scraping_port.py)."""
    title: str
    canonical_title: str
    source_url: str
    content: str
    word_count: int


class ContentChunk(Protocol):
    """Processed content chunk (see storage_port.py)."""
    text: str
    chunk_index: int
    total_chunks: int
    article_title: str
    source_url: str
    word_count: int


class ProcessingPort(ABC):
    """
    Interface for content transformation operations.
    
    Implementations handle parsing MediaWiki API responses,
    chunking text with sentence boundaries, and UTF-8 validation.
    
    These are pure data transformations (no I/O), but abstracted
    behind a port to isolate domain logic from NLP library details
    (NLTK, regex, etc.).
    
    Example implementations:
    - ContentProcessor: Real implementation using NLTK Punkt tokenizer
    - SimpleProcessor: Regex-based fallback for testing
    """
    
    @abstractmethod
    def extract_content(self, api_response: dict) -> str:
        """
        Extract main article text from MediaWiki API response.
        
        Parses structured JSON response from MediaWiki REST API,
        removing navigation, metadata, infoboxes, and non-content elements.
        
        Preserves:
        - Paragraph structure (double newlines between paragraphs)
        - Section headings (if present in API response)
        - List formatting (bullets, numbered lists)
        
        Removes:
        - HTML tags
        - Navigation links
        - Infobox tables
        - "See also" / "References" sections
        - Image captions and file metadata
        
        Args:
            api_response: Raw MediaWiki REST API JSON response.
                         Expected structure (may vary by endpoint):
                         {
                           "title": "Python (programming language)",
                           "extract": "Python is a high-level...",
                           # ... other fields
                         }
        
        Returns:
            Cleaned article text (plain text, UTF-8 encoded).
            Paragraphs separated by double newlines.
            Minimum length: 100 characters (stub article warning if shorter).
        
        Raises:
            ParsingError: Unexpected API response structure.
                         Missing required fields or invalid JSON.
                         Includes context about which field was missing.
        
        Example:
            ```python
            api_response = {
                "title": "Python (programming language)",
                "extract": "Python is a <strong>high-level</strong>...",
            }
            content = processor.extract_content(api_response)
            # "Python is a high-level..." (HTML tags removed)
            ```
        """
        pass
    
    @abstractmethod
    def chunk_content(
        self, 
        article: WikipediaArticle, 
        chunk_size: int = 1000, 
        overlap: int = 100
    ) -> list[ContentChunk]:
        """
        Split article into overlapping chunks respecting sentence boundaries.
        
        Chunks are sized in WORDS (not characters or tokens).
        Overlap region contains complete sentences only.
        Last chunk may be smaller than chunk_size (preserves all content).
        
        Algorithm:
        1. Tokenize article.content into sentences (NLTK Punkt tokenizer)
        2. Group sentences until reaching ~chunk_size words
        3. If next sentence would exceed chunk_size by >20%, start new chunk
        4. Otherwise, include next sentence (preserve semantic unit)
        5. Overlap: Include last ~overlap words from previous chunk
        6. Validate: No mid-sentence cuts, no partial UTF-8 sequences
        
        Args:
            article: WikipediaArticle to chunk.
            
            chunk_size: Target words per chunk (default 1000).
                       Actual chunks may be slightly larger to preserve
                       sentence boundaries (up to +20% tolerance).
            
            overlap: Overlap words between chunks (default 100).
                    Overlap region MUST contain complete sentences.
                    If last sentence in overlap exceeds overlap size,
                    include it anyway (no mid-sentence cuts).
        
        Returns:
            List of ContentChunk objects with metadata.
            
            Empty list if article.content is empty or all whitespace.
            
            Chunks are ordered sequentially (chunk_index 0, 1, 2, ...).
            
            Each chunk has:
            - text: Chunk content (complete sentences)
            - chunk_index: Position in article (0-based)
            - total_chunks: Total chunks from this article
            - article_title: article.canonical_title
            - source_url: article.source_url
            - word_count: Words in this chunk (calculated)
            - overlap_start: Character offset where overlap begins
            - overlap_end: Character offset where overlap ends
        
        Raises:
            ChunkingError: Failed to tokenize sentences or split content.
                          Possible causes:
                          - NLTK Punkt tokenizer not available
                          - Invalid UTF-8 in article.content
                          - Article content too short to chunk
        
        Example:
            ```python
            article = WikipediaArticle(
                title="Python (programming language)",
                content="Python is a high-level language. It was created by Guido...",
                word_count=15234
            )
            chunks = processor.chunk_content(article, chunk_size=1000, overlap=100)
            print(f"Created {len(chunks)} chunks")  # "Created 16 chunks"
            
            # Verify sentence boundaries
            for chunk in chunks:
                assert chunk.text.strip().endswith(('.', '!', '?'))
            ```
        """
        pass
    
    @abstractmethod
    def validate_utf8(self, text: str) -> bool:
        """
        Verify text is valid UTF-8 encoding.
        
        Checks for partial multi-byte sequences that could cause
        corruption when chunking text at arbitrary byte boundaries.
        
        Important for:
        - Wikipedia articles with non-ASCII characters (accents, symbols)
        - Math equations with special characters
        - Non-English articles
        
        Args:
            text: Text to validate (may contain UTF-8 multi-byte characters).
        
        Returns:
            True if text is valid UTF-8 (no partial sequences).
            False if text contains invalid UTF-8 (corrupted or partial).
        
        Example:
            ```python
            valid_text = "Python is a high-level language. É muito bom!"
            assert processor.validate_utf8(valid_text) == True
            
            # Simulated partial UTF-8 (byte string truncated mid-character)
            invalid_text = "Python é ".encode('utf-8')[:-1].decode('utf-8', errors='replace')
            assert processor.validate_utf8(invalid_text) == False
            ```
        """
        pass
    
    @abstractmethod
    def estimate_chunk_count(self, word_count: int, chunk_size: int = 1000) -> int:
        """
        Estimate number of chunks for given word count.
        
        Used for dry-run mode to preview chunk count without
        fetching full article content.
        
        Estimation formula:
            chunks = ceil(word_count / (chunk_size - overlap))
        
        This accounts for overlap reducing effective chunk size.
        
        Args:
            word_count: Total words in article.
            chunk_size: Target words per chunk (default 1000).
        
        Returns:
            Estimated number of chunks (integer, minimum 1).
        
        Example:
            ```python
            word_count = 15234
            estimated = processor.estimate_chunk_count(word_count, chunk_size=1000)
            print(f"Estimated {estimated} chunks")  # "Estimated 16 chunks"
            ```
        """
        pass
