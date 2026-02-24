# Feature Specification: Wikipedia Knowledge Base Scraper

**Feature Branch**: `009-web-scraping`  
**Created**: 2024-02-23  
**Status**: Draft  
**Input**: User description: "Automated Knowledge Base Update via Web Scraping - Scraping educational content from Wikipedia with rate limiting, content processing, error handling, and automatic ChromaDB ingestion. Support CLI-driven scraping with dry-run mode, topic selection, and configurable rate limits. Implement hexagonal architecture with Port/Adapter pattern."

## Clarifications

### Session 2026-02-17

- Q: What data source API should the system use to retrieve Wikipedia content (web scraping HTML vs. MediaWiki API vs. Wikipedia REST API)? → A: Use MediaWiki API (Wikipedia's official REST API at https://en.wikipedia.org/api/rest_v1/)
- Q: How should the system handle third-party API failures (Wikipedia API, ChromaDB) during scraping operations? → A: Retry up to 3 times with exponential backoff before marking as failed, combined with detailed logging for debugging
- Q: What is the data retention policy for vectorized Wikipedia content in ChromaDB? → A: Indefinite retention until explicit deletion via admin CLI command. Wikipedia content is openly licensed, so indefinite storage is appropriate
- Q: What is the target latency for semantic search queries over the ingested Wikipedia content? → A: Under 500ms for 90th percentile semantic queries. This provides production-grade performance with reasonable infrastructure requirements
- Q: What is the scope of search functionality (single-article search within one document vs. course-wide search across all ingested articles)? → A: Course-wide search across all ingested Wikipedia articles (global search across entire ChromaDB collection). This provides maximum value for the knowledge base and RAG system

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual Topic Scraping with Immediate Ingestion (Priority: P1)

A developer needs to enrich the knowledge base with specific educational content from Wikipedia. They run a CLI command specifying topics (Wikipedia article titles), and the system scrapes, processes, and ingests the content into ChromaDB automatically with proper error handling and rate limiting.

**Why this priority**: This is the core value proposition - getting Wikipedia content into the knowledge base. Without this, the feature delivers no value. All other stories build on this foundation.

**Independent Test**: Can be fully tested by running `scraper wikipedia --topics "Python (programming language)" "Machine learning"` and verifying that ChromaDB contains the processed content with proper metadata. Delivers immediate value by enriching the knowledge base with selected topics.

**Acceptance Scenarios**:

1. **Given** ChromaDB is running and accessible, **When** user executes scraping command with 2 valid Wikipedia topics, **Then** system scrapes both articles, processes content into chunks, ingests into ChromaDB, and reports success with statistics (articles processed, chunks created, errors if any)

2. **Given** user specifies a non-existent Wikipedia article, **When** scraping executes, **Then** system logs error for that article, continues processing remaining valid articles, and returns partial success with clear error reporting

3. **Given** network connection fails mid-scrape, **When** error occurs, **Then** system logs the failure, saves already-processed content to ChromaDB, and reports which articles succeeded vs. failed

4. **Given** ChromaDB is unavailable, **When** scraping completes, **Then** system detects connection failure, logs detailed error, and exits with non-zero status code without losing scraped data (can retry ingestion)

---

### User Story 2 - Dry-Run Mode for Planning and Validation (Priority: P2)

A developer wants to preview what will be scraped before executing the actual operation. They use dry-run mode to see article metadata (titles, URLs, estimated content size) without making actual requests to Wikipedia or modifying ChromaDB.

**Why this priority**: Validates requests before execution, prevents accidental large scrapes, and provides confidence. Essential for production use but not required for basic functionality.

**Independent Test**: Can be tested by running `scraper wikipedia --topics "Artificial intelligence" --dry-run` and verifying that output shows article metadata without any Wikipedia requests or ChromaDB changes. Delivers value by letting users validate their scraping plan.

**Acceptance Scenarios**:

1. **Given** user specifies 5 topics with dry-run flag, **When** command executes, **Then** system displays article titles, Wikipedia URLs, and estimated content size WITHOUT making HTTP requests or modifying ChromaDB

2. **Given** user provides mix of valid and invalid topic names in dry-run, **When** command executes, **Then** system shows which topics would succeed vs. fail with clear indicators, allowing user to correct before actual run

---

### User Story 3 - Configurable Rate Limiting (Priority: P2)

A system administrator needs to configure rate limiting to respect Wikipedia's usage policies and avoid being blocked. They set custom rate limits via CLI flags or configuration file, and the system enforces these limits across all HTTP requests.

**Why this priority**: Critical for responsible API usage and avoiding blocks, but reasonable defaults can make it non-blocking for P1. Must be configurable for different use cases (testing vs. production).

**Independent Test**: Can be tested by running `scraper wikipedia --topics "Topic1" "Topic2" --rate-limit 2.0` and measuring actual request intervals to verify enforcement. Delivers value by enabling respectful scraping practices.

**Acceptance Scenarios**:

1. **Given** user sets rate limit to 0.5 requests/second, **When** scraping 10 articles, **Then** system enforces minimum 2-second delay between consecutive Wikipedia requests

2. **Given** no rate limit is specified, **When** scraping executes, **Then** system uses default rate limit of 1 request/second (Wikipedia's recommended guideline)

3. **Given** rate limit is configured in config file and CLI flag is provided, **When** scraping executes, **Then** CLI flag takes precedence over config file value

---

### User Story 4 - Content Processing Pipeline (Priority: P1)

The system automatically processes MediaWiki API JSON responses into clean, structured text suitable for embedding and retrieval. This includes parsing structured API data, text extraction, chunking large articles, and adding metadata for each chunk.

**Why this priority**: Core functionality required for usable knowledge base content. Raw API responses need to be processed into semantic chunks with proper metadata.

**Independent Test**: Can be tested by retrieving a long article (>5000 words) via MediaWiki API and verifying ChromaDB contains multiple chunks with proper overlap, metadata (source, chunk_index), and clean text.

**Acceptance Scenarios**:

1. **Given** MediaWiki API returns structured article content with metadata, **When** processing occurs, **Then** system extracts main article text only, preserves paragraph structure, and excludes navigation/metadata elements

2. **Given** article is >3000 words, **When** chunking occurs, **Then** system creates chunks of ~1000 words with 100-word overlap, preserves sentence boundaries (no mid-sentence cuts), and adds chunk_index metadata

3. **Given** article contains special characters, equations, or non-English text, **When** processing occurs, **Then** system preserves UTF-8 encoding correctly and handles special characters without corruption

---

### User Story 5 - Hexagonal Architecture Implementation (Priority: P3)

The system is architected with clear separation between core business logic (domain) and external systems (Wikipedia, ChromaDB) using Port/Adapter pattern. This enables easy testing, mocking, and future adapter swaps.

**Why this priority**: Architectural quality requirement that improves maintainability and testability but doesn't directly deliver user value. Can be refined after proving core functionality.

**Independent Test**: Can be validated through code review verifying: domain logic has no dependencies on external libraries, ports are defined as interfaces, adapters implement ports, and unit tests can run without Wikipedia/ChromaDB connections using mocks.

**Acceptance Scenarios**:

1. **Given** domain layer defines scraping logic, **When** examining dependencies, **Then** domain code only depends on port interfaces, not concrete implementations (no requests, chromadb imports in domain)

2. **Given** MediaWiki adapter implements content retrieval port, **When** running unit tests, **Then** tests can use mock adapter without actual HTTP requests, proving port/adapter separation

3. **Given** need to add new content source (e.g., educational site), **When** implementing, **Then** can create new adapter implementing existing port without modifying domain logic

---

### Edge Cases

- **MediaWiki API structure change**: System gracefully handles API response parsing failures by logging detailed errors with article URL and continuing with remaining articles
- **Rate limit exceeded despite configuration**: System detects 429 responses from Wikipedia, implements exponential backoff (initial 1s, then 2s, then 4s), and retries up to 3 times before marking article as failed with detailed error logging
- **Massive article (>50k words)**: System caps article processing at 50 chunks (50k words), logs warning about truncation, and includes metadata indicating partial content
- **Concurrent scraping attempts**: Known limitation in V1 - document that concurrent runs may conflict; recommend sequential execution or separate topic sets
- **Duplicate content across scrapes**: System uses article URL as deduplication key; re-scraping same topic updates existing ChromaDB entries rather than creating duplicates
- **ChromaDB collection doesn't exist**: System detects missing collection, creates it automatically with appropriate configuration (embedding model, distance metric), and proceeds with ingestion
- **Partial UTF-8 sequences in chunking**: System uses sentence boundary detection to prevent breaking multi-byte UTF-8 characters across chunk boundaries
- **Wikipedia redirect pages**: System follows redirects transparently, uses final destination URL as canonical identifier
- **Network timeout mid-article**: System implements 30-second timeout per request, retries up to 3 times with exponential backoff (1s, 2s, 4s), logs all attempts with detailed error information, and continues with next article after final failure
- **Empty or stub articles**: System detects articles <100 words, logs informational message, still processes into ChromaDB with metadata flag indicating stub article

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST retrieve content from Wikipedia articles specified by title via CLI arguments using the MediaWiki REST API (https://en.wikipedia.org/api/rest_v1/)
- **FR-002**: System MUST enforce configurable rate limiting with default of 1 request/second to respect Wikipedia usage policies
- **FR-003**: System MUST parse structured content from MediaWiki API response and extract main article text, excluding navigation, metadata, and non-content elements
- **FR-004**: System MUST chunk articles larger than 1000 words into segments with 100-word overlap, preserving sentence boundaries
- **FR-005**: System MUST automatically ingest processed content into ChromaDB with metadata including source URL, scrape timestamp, chunk index, and article title
- **FR-006**: System MUST implement dry-run mode that displays article metadata (title, URL, estimated size) without making HTTP requests or modifying ChromaDB
- **FR-007**: System MUST handle network failures gracefully by logging errors, saving successfully processed content, and reporting partial success/failure statistics
- **FR-008**: System MUST handle ChromaDB connection failures by retrying up to 3 times with exponential backoff (1s, 2s, 4s), logging each attempt with detailed error context, and exiting with non-zero status after exhausting retries
- **FR-009**: System MUST follow hexagonal architecture with Port/Adapter pattern, separating domain logic from infrastructure concerns (MediaWiki API client, ChromaDB client)
- **FR-010**: System MUST accept rate limit configuration via CLI flag (--rate-limit) with precedence over configuration file values
- **FR-011**: System MUST log all operations (scraping, processing, ingestion) with appropriate severity levels (INFO, WARNING, ERROR) to standard output/error
- **FR-012**: System MUST deduplicate content by using article URL as identifier; re-scraping updates existing ChromaDB entries
- **FR-021**: System MUST retain scraped Wikipedia content indefinitely in ChromaDB until explicit deletion via admin CLI command (content is not automatically purged or expired)
- **FR-013**: System MUST handle Wikipedia redirects by following them transparently and using final destination URL as canonical identifier
- **FR-014**: System MUST preserve UTF-8 encoding throughout the pipeline, handling special characters, equations, and non-English text correctly
- **FR-015**: System MUST provide CLI with topic selection via `--topics` flag accepting multiple article titles as arguments
- **FR-016**: System MUST return exit code 0 for complete success, 1 for complete failure, and 2 for partial success (some articles failed)
- **FR-017**: System MUST implement retry logic with exponential backoff (initial delay 1s, doubling each retry: 2s, 4s) for transient failures (429 rate limit, 503 service unavailable, network timeouts), up to 3 retry attempts, with detailed logging of each attempt including error type, article name, and retry count
- **FR-018**: System MUST create ChromaDB collection automatically if it doesn't exist, using appropriate default configuration
- **FR-019**: System MUST NOT implement scheduled/automated scraping in V1; all operations are CLI-driven and user-initiated
- **FR-020**: System MUST validate topic names are non-empty strings before attempting scraping, providing clear error for invalid input
- **FR-022**: System MUST support course-wide semantic search across all ingested Wikipedia articles in the ChromaDB collection, enabling global knowledge retrieval rather than single-article search
- **FR-023**: System MUST structure ChromaDB collection to enable efficient cross-article semantic queries, using appropriate metadata tagging (article_title, source_url) to allow filtering while maintaining global search capability

### Key Entities

- **ScrapingJob**: Represents a single scraping operation including list of topics, configuration (rate limit, dry-run mode), execution status, and statistics (success/fail counts)
- **WikipediaArticle**: Represents retrieved Wikipedia content including title, source URL, MediaWiki API response data, extracted text, retrieval timestamp, and word count
- **ContentChunk**: Represents processed text segment including chunk text (≤1000 words), chunk index, parent article reference, overlap region with adjacent chunks, and metadata for ChromaDB ingestion
- **ScrapingPort**: Interface defining content retrieval operations (fetch article via MediaWiki API, respect rate limit, handle redirects) - implemented by MediaWikiAdapter
- **StoragePort**: Interface defining knowledge base operations (ingest chunks, check for duplicates, create collection, perform course-wide semantic search across all articles) - implemented by ChromaDBAdapter
- **SearchQuery**: Represents a semantic search request including query text, result limit, optional metadata filters (article title, date range), and search scope (always course-wide across entire collection)
- **ProcessingPort**: Interface defining content transformation (parse MediaWiki API JSON response, extract text, chunk content, validate encoding)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can scrape and ingest 10 Wikipedia articles in under 15 seconds (with default 1 req/sec rate limit: ~10 seconds scraping + ~5 seconds processing/ingestion)
- **SC-002**: System successfully processes articles ranging from 500 to 20,000 words without data loss or corruption
- **SC-003**: Content retrieval from ChromaDB returns relevant chunks from ingested articles with >90% semantic accuracy (measured via test queries)
- **SC-004**: System handles 95% of Wikipedia articles without parsing errors (based on sample of 1000 random articles)
- **SC-005**: Dry-run mode executes in <1 second for up to 20 topics, providing instant feedback without external requests
- **SC-006**: Network failures during scraping result in zero data loss for already-processed articles (partial success is preserved)
- **SC-007**: Comprehensive acceptance tests achieve >90% code coverage for domain logic and adapter implementations
- **SC-008**: Documentation enables new developer to run first successful scrape within 5 minutes of reading

### Performance & UX Targets

- **CLI Response Time**: Immediate feedback (<100ms) for command validation and dry-run mode; for actual scraping, progress indicators every 2 seconds
- **Rate Limiting Accuracy**: Enforces configured rate limit within ±50ms tolerance (measured across 100 consecutive requests)
- **Memory Efficiency**: Processes individual articles in streaming fashion; memory usage remains <100MB regardless of article size (no full article buffering)
- **Error Reporting**: All errors include actionable context (article name, error type, suggested resolution) in human-readable format
- **Chunking Quality**: 100% of chunks respect sentence boundaries (no mid-sentence cuts); overlap regions contain complete sentences only
- **Semantic Search Latency**: ChromaDB queries over ingested Wikipedia content must complete within 500ms at 90th percentile, ensuring production-grade retrieval performance with reasonable infrastructure requirements. This applies to course-wide searches across the entire collection of all ingested Wikipedia articles
- **Search Scope**: All semantic queries operate in course-wide mode, searching across all ingested Wikipedia articles in the ChromaDB collection rather than limiting to single articles

### Architectural Quality

- **Port/Adapter Compliance**: Domain logic has zero direct dependencies on external libraries (requests, chromadb); all external interactions through port interfaces
- **Test Isolation**: Unit tests for domain logic run without network/database access using mocked ports (execution time <1 second for full domain test suite)
- **Adapter Replaceability**: Can swap Wikipedia adapter for alternative content source by implementing scraping port without modifying domain logic (verified via second adapter implementation for testing)
- **Configuration Flexibility**: Rate limits, chunk sizes, retry attempts, and timeouts are configurable via CLI flags or config file (12 configurable parameters minimum)

### Documentation Completeness

- **README Updates**: Installation instructions, usage examples for all CLI flags, architecture diagram showing ports/adapters, troubleshooting section for common errors
- **API Documentation**: All port interfaces documented with docstrings explaining parameters, return values, and error conditions
- **Acceptance Test Documentation**: Test scenarios mapped to user stories with clear setup/teardown instructions and expected outcomes
- **Architecture Decision Record**: Document explaining hexagonal architecture choice, port definitions, and adapter responsibilities
