"""CLI commands for Wikipedia scraping.

This module provides Click-based command-line interface for scraping
Wikipedia articles into the CourseFlow knowledge base.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import click

from courseflow.application.scraping_service import ScrapingService
from courseflow.cli.config import (
    chunk_overlap_option,
    chunk_size_option,
    dry_run_option,
    no_ingest_option,
    rate_limit_option,
    retry_attempts_option,
    timeout_option,
    topics_option,
    verbose_option,
)
from courseflow.config import settings
from courseflow.domain.scraping.models import JobStatus, ScrapingConfig

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """Configure console + file logging for scraper commands."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_path = Path(settings.SCRAPER_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )


@click.group()
def scraper():
    """Wikipedia scraper commands for CourseFlow knowledge base."""
    pass


@scraper.command()
@topics_option()
@rate_limit_option()
@dry_run_option()
@no_ingest_option()
@chunk_size_option()
@chunk_overlap_option()
@timeout_option()
@retry_attempts_option()
@verbose_option()
def scrape(
    topics: tuple[str, ...],
    rate_limit: float,
    dry_run: bool,
    no_ingest: bool,
    chunk_size: int,
    chunk_overlap: int,
    timeout: int,
    retry_attempts: int,
    verbose: bool,
) -> None:
    """Scrape Wikipedia articles and ingest into ChromaDB.

    Example:
        scraper scrape --topics "Python (programming language)" --topics "Machine learning"
        scraper scrape -t "Artificial intelligence" --dry-run
        scraper scrape -t "Python" --verbose
    """
    _configure_logging(verbose)

    # Convert tuple to list
    topics_list = list(topics)

    # Create scraping configuration
    config = ScrapingConfig(
        rate_limit=rate_limit,
        retry_attempts=retry_attempts,
        timeout_seconds=timeout,
        dry_run=dry_run,
        no_ingest=no_ingest,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Display configuration
    click.echo("\n" + "=" * 60)
    click.echo("Wikipedia Scraper - CourseFlow Knowledge Base")
    click.echo("=" * 60)
    click.echo(f"Topics: {len(topics_list)}")
    for i, topic in enumerate(topics_list, 1):
        click.echo(f"  {i}. {topic}")
    click.echo(f"Rate limit: {rate_limit} req/sec")
    click.echo(f"Chunk size: {chunk_size} words")
    click.echo(f"Chunk overlap: {chunk_overlap} words")
    click.echo(f"Timeout: {timeout}s")
    click.echo(f"Retry attempts: {retry_attempts}")
    if dry_run:
        click.echo(click.style("MODE: DRY-RUN (preview only)", fg="yellow", bold=True))
    if no_ingest:
        click.echo(click.style("MODE: NO-INGEST (markdown only)", fg="yellow", bold=True))
    click.echo("=" * 60 + "\n")

    # Execute scraping
    try:
        # Run async scraping
        job = asyncio.run(_run_scraping(topics_list, config))

        # Display results
        _display_results(job)

        # Exit with appropriate code
        if job.status == JobStatus.COMPLETED:
            sys.exit(0)
        elif job.status == JobStatus.PARTIAL_SUCCESS:
            sys.exit(2)
        else:
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red", bold=True), err=True)
        logger.exception("Scraping failed")
        sys.exit(1)


async def _run_scraping(topics: list[str], config: ScrapingConfig) -> Any:
    """Run scraping operation asynchronously."""
    service = ScrapingService()
    try:
        return await service.scrape_topics(topics=topics, config=config)
    finally:
        await service.cleanup()


def _display_results(job: Any) -> None:
    """Display scraping results in formatted output."""
    stats = job.statistics

    click.echo("\n" + "=" * 60)
    click.echo("Scraping Results")
    click.echo("=" * 60)

    # Status indicator
    if job.status == JobStatus.COMPLETED:
        click.echo(click.style("✓ Status: COMPLETED", fg="green", bold=True))
    elif job.status == JobStatus.PARTIAL_SUCCESS:
        click.echo(click.style("⚠ Status: PARTIAL SUCCESS", fg="yellow", bold=True))
    else:
        click.echo(click.style("✗ Status: FAILED", fg="red", bold=True))

    # Statistics
    click.echo(f"\nTotal articles: {stats.total_articles}")
    click.echo(click.style(f"Successful: {stats.successful_articles}", fg="green"))
    if stats.failed_articles > 0:
        click.echo(click.style(f"Failed: {stats.failed_articles}", fg="red"))
    click.echo(f"Total chunks created: {stats.total_chunks_created}")
    click.echo(f"Processing time: {stats.total_processing_time_seconds:.2f}s")

    # Display errors if any
    if job.errors:
        click.echo(f"\n{click.style('Errors:', fg='red', bold=True)}")
        for error in job.errors:
            click.echo(f"  • {error.article_title}: {error.error_message}")

    click.echo("=" * 60 + "\n")


@scraper.command()
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Number of results to return")
def search(query: str, limit: int) -> None:
    """Test semantic search across ingested Wikipedia articles.

    Example:
        scraper search "What is machine learning?" --limit 5
    """
    click.echo(f"\nSearching for: {query}\n")

    async def _run_search():
        service = ScrapingService()
        try:
            results = await service.storage_adapter.search(
                query=query,
                top_k=limit,
            )
            return results
        finally:
            await service.cleanup()

    try:
        results = asyncio.run(_run_search())

        if not results:
            click.echo(click.style("No results found.", fg="yellow"))
            return

        click.echo(f"Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            click.echo(f"{i}. {click.style(result['article_title'], bold=True)}")
            click.echo(f"   Relevance: {result['relevance_score']:.3f}")
            click.echo(f"   URL: {result['source_url']}")
            click.echo(f"   Chunk: {result['chunk_index'] + 1}")
            click.echo(f"   Text: {result['text'][:200]}...")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Search failed: {e}", fg="red"), err=True)
        sys.exit(1)


@scraper.command(name="list")
def list_articles() -> None:
    """List all ingested Wikipedia articles."""

    async def _run_list():
        service = ScrapingService()
        try:
            return await service.storage_adapter.list_all_articles()
        finally:
            await service.cleanup()

    try:
        articles = asyncio.run(_run_list())

        if not articles:
            click.echo(click.style("No articles ingested yet.", fg="yellow"))
            return

        click.echo(f"\nIngested Wikipedia Articles ({len(articles)} total):\n")
        for i, article in enumerate(articles, 1):
            click.echo(
                f"{i}. {click.style(article['article_title'], bold=True)} "
                f"({article['total_chunks']} chunks)"
            )
            click.echo(f"   URL: {article['source_url']}")
            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Failed to list articles: {e}", fg="red"), err=True)
        sys.exit(1)


@scraper.command()
@click.argument("article_title")
@click.confirmation_option(
    prompt="Are you sure you want to delete this article and all its chunks?"
)
def delete(article_title: str) -> None:
    """Delete an article and all its chunks from ChromaDB.

    Example:
        scraper delete "Python (programming language)"
    """

    async def _run_delete():
        service = ScrapingService()
        try:
            return await service.storage_adapter.delete_article(article_title)
        finally:
            await service.cleanup()

    try:
        chunks_deleted = asyncio.run(_run_delete())

        if chunks_deleted > 0:
            click.echo(
                click.style(
                    f"✓ Deleted {chunks_deleted} chunks for '{article_title}'",
                    fg="green",
                )
            )
        else:
            click.echo(
                click.style(
                    f"⚠ No chunks found for '{article_title}'",
                    fg="yellow",
                )
            )

    except Exception as e:
        click.echo(
            click.style(f"✗ Failed to delete article: {e}", fg="red"),
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    scraper()
