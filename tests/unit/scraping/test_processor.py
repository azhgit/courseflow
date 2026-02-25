"""Unit tests for ContentProcessor."""

import pytest

from courseflow.domain.scraping.exceptions import ChunkingError, ParsingError
from courseflow.infrastructure.scrapers.processor import ContentProcessor


@pytest.fixture
def processor() -> ContentProcessor:
    return ContentProcessor()


class TestExtractContent:
    """Test content extraction from MediaWiki API responses."""

    @pytest.mark.asyncio
    async def test_extract_from_source_field(self, processor: ContentProcessor) -> None:
        raw = {"source": "Hello world. This is a test article."}
        result = await processor.extract_content(raw)
        assert "Hello world" in result

    @pytest.mark.asyncio
    async def test_extract_from_extract_field(self, processor: ContentProcessor) -> None:
        raw = {"extract": "Plain text extract content."}
        result = await processor.extract_content(raw)
        assert "Plain text extract content" in result

    @pytest.mark.asyncio
    async def test_extract_html_not_supported(self, processor: ContentProcessor) -> None:
        raw = {"html": "<p>content</p>"}
        with pytest.raises(ParsingError, match="HTML response format not supported"):
            await processor.extract_content(raw)

    @pytest.mark.asyncio
    async def test_extract_unexpected_structure(self, processor: ContentProcessor) -> None:
        raw = {"unexpected_key": "value"}
        with pytest.raises(ParsingError, match="Unexpected API response structure"):
            await processor.extract_content(raw)

    @pytest.mark.asyncio
    async def test_extract_removes_html_tags(self, processor: ContentProcessor) -> None:
        raw = {"source": "Hello <b>bold</b> world."}
        result = await processor.extract_content(raw)
        assert "<b>" not in result
        assert "bold" in result

    @pytest.mark.asyncio
    async def test_extract_removes_mediawiki_markup(self, processor: ContentProcessor) -> None:
        raw = {"source": "Hello {{template}} [[link|text]] world."}
        result = await processor.extract_content(raw)
        assert "{{template}}" not in result
        assert "text" in result


class TestChunkContent:
    """Test content chunking with sentence boundaries."""

    @pytest.mark.asyncio
    async def test_single_chunk_for_short_content(self, processor: ContentProcessor) -> None:
        content = "This is a short sentence. Another sentence here."
        chunks = await processor.chunk_content(content, "Test Article", "http://example.com")
        assert len(chunks) == 1
        assert chunks[0]["article_title"] == "Test Article"
        assert chunks[0]["source_url"] == "http://example.com"
        assert chunks[0]["chunk_index"] == 0

    @pytest.mark.asyncio
    async def test_multiple_chunks_for_long_content(self, processor: ContentProcessor) -> None:
        # Create content exceeding chunk_size words
        sentences = ["This is sentence number {i}. " for i in range(200)]
        content = " ".join(sentences)
        chunks = await processor.chunk_content(
            content, "Long Article", "http://example.com", chunk_size=50
        )
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["total_chunks"] == len(chunks)

    @pytest.mark.asyncio
    async def test_empty_content_raises_error(self, processor: ContentProcessor) -> None:
        with pytest.raises(ChunkingError, match="No sentences found"):
            await processor.chunk_content("", "Empty", "http://example.com")

    @pytest.mark.asyncio
    async def test_chunk_metadata_fields(self, processor: ContentProcessor) -> None:
        content = "A simple test sentence. And another one."
        chunks = await processor.chunk_content(content, "Meta Test", "http://example.com/meta")
        chunk = chunks[0]
        assert "text" in chunk
        assert "chunk_index" in chunk
        assert "total_chunks" in chunk
        assert "word_count" in chunk
        assert "created_at" in chunk


class TestValidateUtf8:
    """Test UTF-8 validation."""

    @pytest.mark.asyncio
    async def test_valid_utf8(self, processor: ContentProcessor) -> None:
        assert await processor.validate_utf8("Hello world") is True

    @pytest.mark.asyncio
    async def test_valid_utf8_with_unicode(self, processor: ContentProcessor) -> None:
        assert await processor.validate_utf8("日本語テスト 🎉") is True


class TestEstimateChunkCount:
    """Test chunk count estimation."""

    @pytest.mark.asyncio
    async def test_empty_content_returns_zero(self, processor: ContentProcessor) -> None:
        assert await processor.estimate_chunk_count("") == 0

    @pytest.mark.asyncio
    async def test_short_content_returns_one(self, processor: ContentProcessor) -> None:
        assert await processor.estimate_chunk_count("hello world") == 1

    @pytest.mark.asyncio
    async def test_long_content_returns_multiple(self, processor: ContentProcessor) -> None:
        content = " ".join(["word"] * 2500)
        result = await processor.estimate_chunk_count(content, chunk_size=1000)
        assert result == 3


class TestHelperMethods:
    """Test private helper methods."""

    def test_remove_html_tags(self, processor: ContentProcessor) -> None:
        result = processor._remove_html_tags("<p>Hello <b>world</b></p>")  # noqa: SLF001
        assert result == "Hello world"

    def test_remove_mediawiki_templates(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup("Before {{cite web|url=x}} after")  # noqa: SLF001
        assert "{{" not in result
        assert "Before" in result

    def test_remove_mediawiki_file_refs(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup("Text [[File:image.png]] more")  # noqa: SLF001
        assert "[[File:" not in result

    def test_remove_mediawiki_image_refs(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup("Text [[Image:photo.jpg]] more")  # noqa: SLF001
        assert "[[Image:" not in result

    def test_wiki_link_to_text(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup("See [[Wikipedia|the site]] now")  # noqa: SLF001
        assert "the site" in result
        assert "[[" not in result

    def test_remove_external_links(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup(  # noqa: SLF001
            "Click [https://example.com here] please"
        )
        assert "here" in result
        assert "https://" not in result

    def test_remove_ref_tags(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup(  # noqa: SLF001
            "Fact<ref name='x'>citation</ref> here"
        )
        assert "<ref" not in result

    def test_remove_bold_italic(self, processor: ContentProcessor) -> None:
        result = processor._remove_mediawiki_markup("'''bold''' and ''italic''")  # noqa: SLF001
        assert "'''" not in result
        assert "''" not in result

    def test_normalize_whitespace(self, processor: ContentProcessor) -> None:
        result = processor._normalize_whitespace("  hello   world  \n\n  test  ")  # noqa: SLF001
        assert result == "hello world test"

    def test_get_overlap_sentences_empty(self, processor: ContentProcessor) -> None:
        result = processor._get_overlap_sentences([], 100)  # noqa: SLF001
        assert result == []

    def test_get_overlap_sentences_returns_tail(self, processor: ContentProcessor) -> None:
        sentences = ["First sentence.", "Second sentence.", "Third sentence."]
        result = processor._get_overlap_sentences(sentences, 5)  # noqa: SLF001
        assert len(result) >= 1
        assert result[-1] == "Third sentence."
