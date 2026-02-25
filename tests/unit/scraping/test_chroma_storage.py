"""Unit tests for ChromaDBStorageAdapter (mocked dependencies)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from courseflow.domain.scraping.exceptions import StorageError


class TestChromaDBStorageAdapterHelpers:
    """Test helper methods that don't require ChromaDB."""

    def test_generate_chunk_id(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        chunk_id = adapter._generate_chunk_id("https://en.wikipedia.org/wiki/Python", 0)  # noqa: SLF001
        assert "_0" in chunk_id
        assert len(chunk_id) > 2

    def test_generate_chunk_id_deterministic(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        id1 = adapter._generate_chunk_id("https://example.com/article", 1)  # noqa: SLF001
        id2 = adapter._generate_chunk_id("https://example.com/article", 1)  # noqa: SLF001
        assert id1 == id2

    def test_generate_chunk_id_different_for_different_chunks(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        id1 = adapter._generate_chunk_id("https://example.com/article", 0)  # noqa: SLF001
        id2 = adapter._generate_chunk_id("https://example.com/article", 1)  # noqa: SLF001
        assert id1 != id2


class TestChromaDBStorageAdapterInit:
    """Test initialization error handling."""

    @patch("courseflow.infrastructure.scrapers.chroma_storage.chromadb")
    @patch("courseflow.infrastructure.scrapers.chroma_storage.settings")
    def test_init_failure_raises_storage_error(
        self, mock_settings: MagicMock, mock_chromadb: MagicMock
    ) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        mock_settings.CHROMA_PERSIST_DIR = "/tmp/test_chroma"
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.GEMINI_EMBEDDING_MODEL = "test-model"
        mock_settings.SCRAPER_EMBEDDING_RPS = 1.0
        mock_chromadb.PersistentClient.side_effect = Exception("Connection failed")

        with pytest.raises(StorageError, match="Failed to initialize ChromaDB"):
            ChromaDBStorageAdapter(persist_dir="/tmp/test_chroma")


class TestChromaDBIngestChunks:
    """Test ingest_chunks method."""

    @pytest.mark.asyncio
    async def test_ingest_empty_returns_zero(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        result = await adapter.ingest_chunks([], "Test Article")
        assert result == 0


class TestChromaDBCheckArticle:
    """Test check_article_exists method."""

    @pytest.mark.asyncio
    async def test_check_article_exists_true(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["id1"]}
        adapter.collection = mock_collection

        result = await adapter.check_article_exists("Test")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_article_exists_false(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        adapter.collection = mock_collection

        result = await adapter.check_article_exists("Nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_article_exists_error(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.side_effect = Exception("DB error")
        adapter.collection = mock_collection

        with pytest.raises(StorageError, match="Failed to check article existence"):
            await adapter.check_article_exists("Test")


class TestChromaDBDeleteArticle:
    """Test delete_article method."""

    @pytest.mark.asyncio
    async def test_delete_article_with_chunks(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": ["id1", "id2"]}
        adapter.collection = mock_collection

        result = await adapter.delete_article("Test")
        assert result == 2
        mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])

    @pytest.mark.asyncio
    async def test_delete_article_no_chunks(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        adapter.collection = mock_collection

        result = await adapter.delete_article("Nonexistent")
        assert result == 0
        mock_collection.delete.assert_not_called()


class TestChromaDBGetArticleMetadata:
    """Test get_article_metadata method."""

    @pytest.mark.asyncio
    async def test_get_metadata_not_found(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        adapter.collection = mock_collection

        result = await adapter.get_article_metadata("Nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_metadata_found(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2"],
            "metadatas": [
                {
                    "source_url": "https://en.wikipedia.org/wiki/Test",
                    "scrape_timestamp": "2024-01-01T00:00:00",
                },
                {
                    "source_url": "https://en.wikipedia.org/wiki/Test",
                    "scrape_timestamp": "2024-01-02T00:00:00",
                },
            ],
        }
        adapter.collection = mock_collection

        result = await adapter.get_article_metadata("Test")
        assert result is not None
        assert result["article_title"] == "Test"
        assert result["total_chunks"] == 2
        assert result["created_at"] == "2024-01-01T00:00:00"
        assert result["last_updated"] == "2024-01-02T00:00:00"


class TestChromaDBListArticles:
    """Test list_all_articles method."""

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"metadatas": []}
        adapter.collection = mock_collection

        result = await adapter.list_all_articles()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_groups_by_title(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "metadatas": [
                {"article_title": "Python", "source_url": "http://a", "scrape_timestamp": "t1"},
                {"article_title": "Python", "source_url": "http://a", "scrape_timestamp": "t2"},
                {"article_title": "Java", "source_url": "http://b", "scrape_timestamp": "t3"},
            ],
        }
        adapter.collection = mock_collection

        result = await adapter.list_all_articles()
        assert len(result) == 2
        titles = {r["article_title"] for r in result}
        assert titles == {"Python", "Java"}

    @pytest.mark.asyncio
    async def test_list_none_metadatas(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"metadatas": None}
        adapter.collection = mock_collection

        result = await adapter.list_all_articles()
        assert result == []


class TestChromaDBClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter

        adapter = object.__new__(ChromaDBStorageAdapter)
        adapter._embedding_client = AsyncMock()
        await adapter.close()
        adapter._embedding_client.close.assert_called_once()
