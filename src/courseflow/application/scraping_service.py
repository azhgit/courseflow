"""Application layer service for Wikipedia scraping.

This module coordinates between the domain orchestrator and infrastructure
adapters, implementing the use case logic for Wikipedia scraping.
"""

import logging
from uuid import uuid4

from courseflow.config import settings
from courseflow.domain.scraping.models import (
    JobStatistics,
    ScrapingConfig,
    ScrapingJob,
)
from courseflow.domain.scraping.services import ScrapingOrchestrator
from courseflow.infrastructure.scrapers.chroma_storage import ChromaDBStorageAdapter
from courseflow.infrastructure.scrapers.mediawiki import MediaWikiAdapter
from courseflow.infrastructure.scrapers.processor import ContentProcessor

logger = logging.getLogger(__name__)


class ScrapingService:
    """Application service for Wikipedia scraping use cases.

    Coordinates between domain orchestrator and infrastructure adapters,
    handles transaction boundaries and dependency injection.
    """

    def __init__(
        self,
        base_url: str | None = None,
        user_agent: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        """Initialize scraping service.

        Args:
            base_url: MediaWiki API base URL (default: from settings)
            user_agent: User-Agent header (default: from settings)
            collection_name: ChromaDB collection name (default: from settings)
        """
        # Initialize infrastructure adapters
        self.mediawiki_adapter = MediaWikiAdapter(
            base_url=base_url or settings.MEDIAWIKI_BASE_URL,
            rate_limit=settings.MEDIAWIKI_RATE_LIMIT,
            timeout_seconds=settings.MEDIAWIKI_TIMEOUT_SECONDS,
            user_agent=user_agent or settings.MEDIAWIKI_USER_AGENT,
        )

        self.storage_adapter = ChromaDBStorageAdapter(
            collection_name=collection_name or settings.CHROMA_COLLECTION_NAME,
        )

        self.processor = ContentProcessor()

        # Initialize domain orchestrator
        self.orchestrator = ScrapingOrchestrator(
            scraping_port=self.mediawiki_adapter,
            storage_port=self.storage_adapter,
            processing_port=self.processor,
        )

    async def scrape_topics(
        self,
        topics: list[str],
        config: ScrapingConfig | None = None,
    ) -> ScrapingJob:
        """Scrape Wikipedia articles for given topics.

        Args:
            topics: List of Wikipedia article titles to scrape
            config: Scraping configuration (default: uses defaults)

        Returns:
            Completed scraping job with results

        Raises:
            ValueError: If topics list is invalid
        """
        # Validate topics
        if not topics:
            raise ValueError("Topics list cannot be empty")

        if len(topics) > 100:
            raise ValueError("Cannot scrape more than 100 topics at once")

        # Use default config if not provided
        if config is None:
            config = ScrapingConfig()

        # Create scraping job
        job = ScrapingJob(
            id=uuid4(),
            topics=topics,
            config=config,
            statistics=JobStatistics(
                total_articles=0,
                successful_articles=0,
                failed_articles=0,
                total_chunks_created=0,
                total_processing_time_seconds=0.0,
            ),
        )

        logger.info(f"Starting scraping job for {len(topics)} topics")

        # Execute scraping through orchestrator
        try:
            job = await self.orchestrator.execute(job)
            logger.info(
                f"Scraping job completed: {job.statistics.successful_articles}/"
                f"{job.statistics.total_articles} articles succeeded"
            )
            return job

        except Exception as e:
            logger.error(f"Scraping job failed: {e}")
            raise

        finally:
            # Cleanup connections
            await self.mediawiki_adapter.close()
            await self.storage_adapter.close()

    async def preview_scraping(
        self,
        topics: list[str],
        chunk_size: int = 1000,
    ) -> dict[str, list[dict[str, str | int]]]:
        """Preview scraping operation without actual execution (dry-run).

        Args:
            topics: List of Wikipedia article titles to preview
            chunk_size: Target chunk size for estimation

        Returns:
            Dictionary with preview information for each topic
        """
        if not topics:
            raise ValueError("Topics list cannot be empty")

        preview_results = []

        for topic in topics:
            try:
                # Validate article exists
                exists = await self.mediawiki_adapter.validate_article_exists(topic)

                if exists:
                    # Estimate chunk count (simple heuristic)
                    # In real implementation, would fetch and analyze content
                    preview_results.append({
                        "topic": topic,
                        "status": "would_succeed",
                        "estimated_chunks": "5-20",  # Placeholder estimation
                        "source_url": f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
                    })
                else:
                    preview_results.append({
                        "topic": topic,
                        "status": "would_fail",
                        "error": "Article not found (404)",
                        "estimated_chunks": 0,
                    })

            except Exception as e:
                preview_results.append({
                    "topic": topic,
                    "status": "would_fail",
                    "error": str(e),
                    "estimated_chunks": 0,
                })

        return {
            "preview": preview_results,
            "total_topics": len(topics),
            "estimated_total_chunks": sum(
                int(r.get("estimated_chunks", 0))
                if isinstance(r.get("estimated_chunks"), int)
                else 10  # Default estimate
                for r in preview_results
            ),
        }

    async def cleanup(self) -> None:
        """Cleanup resources and connections."""
        await self.mediawiki_adapter.close()
        await self.storage_adapter.close()
