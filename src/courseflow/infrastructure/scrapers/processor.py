"""Content processing adapter implementation.

This module implements the ProcessingPort interface for extracting clean text
from MediaWiki API responses and chunking content with sentence boundaries.
"""

import re
from datetime import UTC, datetime
from typing import Any

import nltk

from courseflow.domain.scraping.exceptions import ChunkingError, ParsingError
from courseflow.domain.scraping.ports import ProcessingPort


class ContentProcessor(ProcessingPort):
    """Content processor implementing ProcessingPort interface.

    Handles text extraction from MediaWiki API responses and chunking
    with NLTK sentence tokenization for clean boundaries.
    """

    def __init__(self) -> None:
        """Initialize content processor.

        Ensures NLTK punkt tokenizer is available.
        """
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)

    async def extract_content(self, raw_api_response: dict[str, Any]) -> str:
        """Extract clean text content from MediaWiki API response.

        Args:
            raw_api_response: Raw JSON response from MediaWiki REST API

        Returns:
            Clean plain text content

        Raises:
            ParsingError: Invalid or unexpected API response structure
        """
        try:
            # MediaWiki REST API v1 structure
            if "source" in raw_api_response:
                # Parse wikitext source
                content = raw_api_response["source"]
            elif "html" in raw_api_response:
                # Parse HTML (would need html2text library)
                raise ParsingError("HTML response format not supported yet")
            elif "extract" in raw_api_response:
                # Plain text extract (from summary endpoint)
                content = raw_api_response["extract"]
            else:
                raise ParsingError(f"Unexpected API response structure: {raw_api_response.keys()}")

            # Remove HTML tags if present
            content = self._remove_html_tags(content)

            # Remove MediaWiki markup
            content = self._remove_mediawiki_markup(content)

            # Normalize whitespace
            content = self._normalize_whitespace(content)

            # Validate UTF-8
            if not await self.validate_utf8(content):
                raise ParsingError("Content contains invalid UTF-8 sequences")

            return content

        except KeyError as e:
            raise ParsingError(f"Missing expected field in API response: {e}") from e
        except Exception as e:
            raise ParsingError(f"Failed to extract content: {e}") from e

    async def chunk_content(
        self,
        content: str,
        article_title: str,
        source_url: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> list[dict[str, Any]]:
        """Chunk article content with sentence boundaries and overlap.

        Args:
            content: Article plain text content
            article_title: Article title for metadata
            source_url: Wikipedia URL for metadata
            chunk_size: Target chunk size in words (default: 1000)
            chunk_overlap: Overlap between chunks in words (default: 100)

        Returns:
            List of chunk dictionaries

        Raises:
            ChunkingError: Failed to chunk content
        """
        try:
            # Tokenize into sentences
            sentences = nltk.sent_tokenize(content)

            if not sentences:
                raise ChunkingError("No sentences found in content", article_title)

            chunks = []
            current_chunk = []
            current_word_count = 0
            chunk_index = 0

            # Build chunks respecting sentence boundaries
            for sentence in sentences:
                sentence_words = len(sentence.split())

                # If adding this sentence exceeds target, save current chunk
                if current_word_count + sentence_words > chunk_size and current_chunk:
                    chunks.append(
                        self._create_chunk_dict(
                            current_chunk, chunk_index, article_title, source_url
                        )
                    )
                    chunk_index += 1

                    # Start new chunk with overlap from previous
                    overlap_sentences = self._get_overlap_sentences(current_chunk, chunk_overlap)
                    current_chunk = overlap_sentences
                    current_word_count = sum(len(s.split()) for s in current_chunk)

                current_chunk.append(sentence)
                current_word_count += sentence_words

            # Add final chunk if not empty
            if current_chunk:
                chunks.append(
                    self._create_chunk_dict(current_chunk, chunk_index, article_title, source_url)
                )

            # Update total_chunks for all chunks
            total_chunks = len(chunks)
            for chunk in chunks:
                chunk["total_chunks"] = total_chunks

            return chunks

        except Exception as e:
            if isinstance(e, ChunkingError):
                raise
            raise ChunkingError(f"Failed to chunk content: {e}", article_title) from e

    async def validate_utf8(self, text: str) -> bool:
        """Validate text is valid UTF-8 without partial multibyte sequences.

        Args:
            text: Text to validate

        Returns:
            True if valid UTF-8, False if corrupted
        """
        try:
            # Try encoding and decoding to detect invalid sequences
            text.encode("utf-8").decode("utf-8")
            return True
        except (UnicodeDecodeError, UnicodeEncodeError):
            return False

    async def estimate_chunk_count(self, content: str, chunk_size: int = 1000) -> int:
        """Estimate number of chunks for article content.

        Args:
            content: Article plain text content
            chunk_size: Target chunk size in words

        Returns:
            Estimated number of chunks
        """
        word_count = len(content.split())
        if word_count == 0:
            return 0

        # Simple estimation: total_words / chunk_size, rounded up
        estimated = (word_count + chunk_size - 1) // chunk_size
        return max(1, estimated)

    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags from text."""
        # Simple regex-based HTML tag removal
        clean = re.sub(r"<[^>]+>", "", text)
        return clean

    def _remove_mediawiki_markup(self, text: str) -> str:
        """Remove MediaWiki markup (templates, links, etc.)."""
        # Remove templates: {{template}}
        text = re.sub(r"\{\{[^}]+\}\}", "", text)

        # Remove file/image references: [[File:...]]
        text = re.sub(r"\[\[File:[^\]]+\]\]", "", text)
        text = re.sub(r"\[\[Image:[^\]]+\]\]", "", text)

        # Convert wiki links [[link|text]] to just text
        text = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", text)

        # Remove external links markup
        text = re.sub(r"\[https?://[^\s\]]+ ([^\]]+)\]", r"\1", text)

        # Remove ref tags: <ref>...</ref>
        text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)

        # Remove bold/italic markup
        text = re.sub(r"'{2,}", "", text)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces/newlines with single space
        text = re.sub(r"\s+", " ", text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    def _create_chunk_dict(
        self, sentences: list[str], chunk_index: int, article_title: str, source_url: str
    ) -> dict[str, Any]:
        """Create chunk dictionary from sentences."""
        text = " ".join(sentences)
        word_count = len(text.split())

        return {
            "text": text,
            "chunk_index": chunk_index,
            "total_chunks": 0,  # Will be updated later
            "article_title": article_title,
            "source_url": source_url,
            "word_count": word_count,
            "overlap_start": 0,
            "overlap_end": len(text),
            "created_at": datetime.now(UTC),
        }

    def _get_overlap_sentences(self, sentences: list[str], target_overlap_words: int) -> list[str]:
        """Get sentences from end of list to create overlap of target words."""
        if not sentences:
            return []

        overlap_sentences = []
        word_count = 0

        # Take sentences from end until we reach target overlap
        for sentence in reversed(sentences):
            sentence_words = len(sentence.split())
            if word_count + sentence_words > target_overlap_words and overlap_sentences:
                break
            overlap_sentences.insert(0, sentence)
            word_count += sentence_words

        return overlap_sentences
