"""Domain services for Wikipedia scraping.

This module implements the ScrapingOrchestrator domain service that
orchestrates the scraping workflow using port interfaces.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from courseflow.domain.scraping.exceptions import ScrapingError
from courseflow.domain.scraping.models import (
    ArticleError,
    JobStatistics,
    JobStatus,
    ScrapingConfig,
    ScrapingJob,
    WikipediaArticle,
)
from courseflow.domain.scraping.ports import ProcessingPort, ScrapingPort, StoragePort

logger = logging.getLogger(__name__)


class ScrapingOrchestrator:
    """Domain service orchestrating Wikipedia scraping workflow.

    Coordinates between scraping, processing, and storage ports to
    implement the complete scraping flow with error handling and
    statistics tracking.

    Attributes:
        scraping_port: Port for fetching Wikipedia content
        storage_port: Port for ChromaDB operations
        processing_port: Port for content processing
    """

    def __init__(
        self,
        scraping_port: ScrapingPort,
        storage_port: StoragePort,
        processing_port: ProcessingPort,
    ) -> None:
        """Initialize scraping orchestrator.

        Args:
            scraping_port: Port for fetching Wikipedia content
            storage_port: Port for ChromaDB operations
            processing_port: Port for content processing
        """
        self.scraping_port = scraping_port
        self.storage_port = storage_port
        self.processing_port = processing_port

    async def execute(
        self,
        job: ScrapingJob,
    ) -> ScrapingJob:
        """Execute scraping job for all topics.

        Args:
            job: Scraping job to execute

        Returns:
            Updated job with final status and statistics
        """
        logger.info(f"Starting scraping job {job.id} with {len(job.topics)} topics")

        # Update job status to RUNNING
        job.status = JobStatus.RUNNING
        start_time = datetime.now(UTC)

        # Initialize statistics
        successful_count = 0
        failed_count = 0
        total_chunks = 0
        errors = []

        # Process each topic
        for topic in job.topics:
            try:
                if job.config.dry_run:
                    # Dry-run mode: just validate and estimate
                    logger.info(f"[DRY-RUN] Would scrape: {topic}")
                    successful_count += 1
                    continue

                # Fetch article
                logger.info(f"Fetching article: {topic}")
                article_data = await self.scraping_port.fetch_article(topic)

                # Extract and process content using raw API response
                logger.info(f"Processing content for: {article_data['canonical_title']}")
                content = await self.processing_port.extract_content(
                    article_data["raw_api_response"]
                )

                # Create WikipediaArticle model with processed content
                # Remove raw_api_response before passing to model
                model_data = {k: v for k, v in article_data.items() if k != "raw_api_response"}
                model_data["content"] = content
                article = WikipediaArticle(**model_data)

                # Chunk content
                logger.info(f"Chunking content for: {article.canonical_title}")
                chunks = await self.processing_port.chunk_content(
                    content=content,
                    article_title=article.canonical_title,
                    source_url=str(article.source_url),
                    chunk_size=job.config.chunk_size,
                    chunk_overlap=job.config.chunk_overlap,
                )

                logger.info(f"Created {len(chunks)} chunks for: {article.canonical_title}")

                # Ingest to ChromaDB
                logger.info(f"Ingesting chunks for: {article.canonical_title}")
                chunks_ingested = await self.storage_port.ingest_chunks(
                    chunks=chunks,
                    article_title=article.canonical_title,
                )

                logger.info(
                    f"Successfully ingested {chunks_ingested} chunks for: {article.canonical_title}"
                )

                successful_count += 1
                total_chunks += chunks_ingested

            except ScrapingError as e:
                # Collect error for this article
                logger.error(f"Failed to process article '{topic}': {e}")
                error_type = type(e).__name__.replace("Error", "").lower()

                errors.append(
                    ArticleError(
                        article_title=topic,
                        error_type=error_type,
                        error_message=str(e),
                        retry_count=job.config.retry_attempts,
                    )
                )
                failed_count += 1

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error processing article '{topic}': {e}")
                errors.append(
                    ArticleError(
                        article_title=topic,
                        error_type="parsing",
                        error_message=f"Unexpected error: {e}",
                        retry_count=0,
                    )
                )
                failed_count += 1

        # Calculate final statistics
        end_time = datetime.now(UTC)
        processing_time = (end_time - start_time).total_seconds()

        job.statistics = JobStatistics(
            total_articles=len(job.topics),
            successful_articles=successful_count,
            failed_articles=failed_count,
            total_chunks_created=total_chunks,
            total_processing_time_seconds=processing_time,
        )

        job.errors = errors
        job.end_time = end_time

        # Determine final job status
        if successful_count == len(job.topics):
            job.status = JobStatus.COMPLETED
            logger.info(f"Job {job.id} completed successfully")
        elif successful_count == 0:
            job.status = JobStatus.FAILED
            logger.error(f"Job {job.id} failed completely")
        else:
            job.status = JobStatus.PARTIAL_SUCCESS
            logger.warning(
                f"Job {job.id} completed with partial success: "
                f"{successful_count}/{len(job.topics)} articles succeeded"
            )

        return job
