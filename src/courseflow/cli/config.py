"""CLI configuration and defaults for Wikipedia scraping.

This module defines Click option definitions and default values for
the scraper CLI commands.
"""

import click

# Default configuration values
DEFAULT_RATE_LIMIT = 1.0  # requests per second
DEFAULT_CHUNK_SIZE = 1000  # words
DEFAULT_CHUNK_OVERLAP = 100  # words
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RETRY_ATTEMPTS = 3

# Click option definitions for reuse across commands


def topics_option():
    """Click option for article topics."""
    return click.option(
        "--topics",
        "-t",
        multiple=True,
        required=True,
        help="Wikipedia article titles to scrape (can specify multiple)",
    )


def rate_limit_option():
    """Click option for rate limiting."""
    return click.option(
        "--rate-limit",
        type=float,
        default=DEFAULT_RATE_LIMIT,
        help=f"Requests per second (default: {DEFAULT_RATE_LIMIT})",
    )


def dry_run_option():
    """Click option for dry-run mode."""
    return click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Preview mode without actual scraping",
    )


def no_ingest_option():
    """Click option for skipping Chroma ingestion."""
    return click.option(
        "--no-ingest",
        is_flag=True,
        default=False,
        help="Save markdown output but skip ChromaDB ingestion",
    )


def chunk_size_option():
    """Click option for chunk size."""
    return click.option(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Target words per chunk (default: {DEFAULT_CHUNK_SIZE})",
    )


def chunk_overlap_option():
    """Click option for chunk overlap."""
    return click.option(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help=f"Overlap words between chunks (default: {DEFAULT_CHUNK_OVERLAP})",
    )


def timeout_option():
    """Click option for HTTP timeout."""
    return click.option(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )


def retry_attempts_option():
    """Click option for retry attempts."""
    return click.option(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Maximum retry attempts (default: {DEFAULT_RETRY_ATTEMPTS})",
    )


def verbose_option():
    """Click option for verbose logging."""
    return click.option(
        "--verbose",
        "-v",
        is_flag=True,
        default=False,
        help="Enable verbose debug logging",
    )
