# 009 - Wikipedia Knowledge Base Scraper

## Summary
This feature adds a CLI-driven Wikipedia ingestion pipeline that fetches article content, processes it into chunks, and stores it in ChromaDB for RAG retrieval.

## Key Capabilities
- Topic-based scraping via CLI.
- MediaWiki API integration (official source).
- Configurable rate limiting (`--rate-limit`) with safe default.
- Retry with exponential backoff for transient failures.
- Content processing and chunking with metadata.
- Automatic ChromaDB ingestion and deduplication by canonical URL.
- Dry-run mode for planning without DB writes.

## Primary CLI Flow
```bash
python -m courseflow.cli.scraper --topics "French_Revolution" "World_War_I"
```

Useful options:
- `--dry-run`
- `--rate-limit <float>`
- topic list for batch operations

## Test Guide
### Automated
```bash
pytest tests/unit/scraping -v
pytest tests/integration/scrapers -v
```

### Manual Smoke Test
1) Run dry-run on a known topic.
2) Run real scrape for 1-2 topics.
3) Verify output documents and Chroma ingestion.
4) Query API for one scraped topic and confirm retrieval.

### Failure Cases
- Non-existent topic should be reported without crashing entire run.
- Temporary HTTP/DB failures should retry and log attempts.

## Success Signals
- Scraped topics become searchable in RAG results.
- CLI reports clear success/failure statistics.
- Re-scraping updates existing entries instead of duplicating.
