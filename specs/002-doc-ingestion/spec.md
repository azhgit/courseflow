# Feature Specification: Document Ingestion and Knowledge Base Management

**Feature Branch**: `1-doc-ingestion`  
**Created**: 2025-02-07  
**Status**: Draft  
**Input**: User description: "As a content administrator, I want to upload educational documents (markdown, PDF, plain text) into the knowledge base so that learners can query against up-to-date, curated content across any subject."

## Clarifications

### Session 2026-02-12

- Q: Duplicate detection hashing strategy → A: Hash normalized content (SHA-256) after stripping whitespace/line endings
- Q: Chunking boundary strategy when token limits and sentence boundaries conflict → A: Sentence integrity is strict priority; token range (300-500) is a target but can be exceeded to avoid mid-sentence splits
- Q: Subject tag management strategy → A: Predefined list of subjects maintained in database/config; content admin selects from dropdown; list extensible via admin interface
- Q: Rate limit scope when Gemini 15 RPM limit reached → A: Global quota management system-wide; queue all ingestion requests fairly; respect 15 RPM limit across all concurrent uploads
- Q: Observability/logging strategy → A: Structured logging (request_id, document_id, chunks_created, ingestion_time_ms, rate_limit_queue_time); metrics for throughput/error rates; no distributed tracing (v2)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Document Upload (Priority: P1)

As a content administrator, I need to upload a single educational document and have it immediately available for student queries, so that I can quickly publish new learning materials.

**Why this priority**: This is the core value proposition - getting content into the system. Without this, no other features matter. It's the minimum viable feature that delivers immediate value.

**Independent Test**: Can be fully tested by uploading a markdown file via API, verifying successful ingestion response, and confirming the content is queryable through the existing query endpoint. Delivers standalone value of "content is now searchable."

**Acceptance Scenarios**:

1. **Given** a content administrator has a 3000-word markdown file on biology, **When** they upload it via the ingestion API endpoint, **Then** they receive a success response within 10 seconds with the number of chunks created and ingestion time
2. **Given** a document was just successfully ingested, **When** a learner queries the system about topics from that document, **Then** the query returns relevant chunks from the newly ingested content
3. **Given** a content administrator has a plain text file (.txt) containing course notes, **When** they upload it, **Then** the system processes it and confirms successful ingestion with chunk count
4. **Given** a content administrator has a PDF document, **When** they upload it, **Then** the system extracts plain text and creates queryable chunks maintaining sentence integrity

---

### User Story 2 - Idempotent Re-upload Protection (Priority: P2)

As a content administrator, I need the system to prevent duplicate content when I accidentally upload the same document twice, so that the knowledge base stays clean and search results aren't polluted with duplicates.

**Why this priority**: Critical for data quality and user experience, but not needed for initial content ingestion. Prevents a common mistake that degrades search quality over time.

**Independent Test**: Can be fully tested by uploading the same file twice and verifying that the second upload is skipped with no new chunks created. Delivers the value of "duplicate prevention" independently.

**Acceptance Scenarios**:

1. **Given** a document has already been successfully ingested, **When** the same file is uploaded again with identical content, **Then** the system returns a success response indicating the upload was skipped and no new chunks were created
2. **Given** a document was previously ingested, **When** the same filename is uploaded but with different content, **Then** the system treats it as a new document and creates new chunks
3. **Given** multiple administrators are working concurrently, **When** two administrators attempt to upload the same file simultaneously, **Then** the system ensures only one successful ingestion occurs and the duplicate is rejected

---

### User Story 3 - Multi-Subject Document Organization (Priority: P3)

As a content administrator, I need to tag documents with subject metadata (biology, history, mathematics, etc.) during upload, so that learners can filter and query content specific to their area of study.

**Why this priority**: Enhances organization and search relevance but isn't blocking for basic functionality. The system can ingest and serve content without subject tagging, though less effectively.

**Independent Test**: Can be fully tested by uploading documents with different subject tags and verifying that queries can filter by subject. Delivers the value of "subject-specific search" independently.

**Acceptance Scenarios**:

1. **Given** a content administrator is uploading a biology textbook chapter, **When** they specify "biology" as the subject metadata, **Then** all chunks from that document are tagged with the biology subject
2. **Given** documents from multiple subjects are in the knowledge base, **When** a learner queries with a subject filter (e.g., "biology"), **Then** only chunks from biology documents are returned in results
3. **Given** a content administrator uploads a document without specifying a subject, **Then** the system accepts the upload and stores it with a default "general" subject tag

---

### User Story 4 - Automatic Retry with Graceful Failure Handling (Priority: P2)

As a content administrator, I need the system to automatically handle temporary failures during document processing (such as rate limits or network issues), so that I don't have to manually retry uploads or lose my work.

**Why this priority**: Essential for reliability and administrator experience, especially when dealing with external service quotas. Prevents frustration and data loss but isn't needed for basic happy-path functionality.

**Independent Test**: Can be fully tested by simulating rate limit conditions and verifying automatic retry with exponential backoff, followed by rollback if retries are exhausted. Delivers the value of "reliable ingestion under constraints."

**Acceptance Scenarios**:

1. **Given** a large document requires multiple semantic processing calls, **When** a rate limit is encountered mid-processing, **Then** the system automatically retries with exponential backoff and completes the ingestion successfully
2. **Given** a semantic processing service is temporarily unavailable, **When** automatic retries are exhausted after maximum attempts, **Then** the system rolls back any partial chunks and returns a clear failure message to the administrator
3. **Given** a document upload is in progress, **When** a transient network error occurs, **Then** the system retries the failed operation without requiring administrator intervention
4. **Given** a document processing encounters repeated failures, **When** the maximum retry count is reached, **Then** the administrator receives a detailed error report indicating what failed and why, with no partial/corrupted data in the knowledge base

---

### Edge Cases

- What happens when a document is empty (0 bytes or whitespace-only)?
  - System rejects with validation error indicating minimum content requirements
  
- What happens when a document exceeds reasonable size limits (e.g., 50MB)?
  - System rejects with validation error indicating maximum file size
  
- What happens when a PDF is corrupted or password-protected?
  - System returns clear error message indicating the file cannot be processed
  
- What happens when document content contains only special characters or non-textual data?
  - System processes what it can extract; if no meaningful text, returns validation error
  
- What happens when chunk boundaries would split critical content (equations, code blocks, tables)?
  - System uses sentence-boundary detection to maintain chunk integrity; if a single sentence exceeds chunk size, it becomes its own chunk
  
- What happens when the same document is uploaded during an existing upload of that same document?
  - System detects in-progress upload and rejects duplicate with clear message
  
- What happens when metadata fields contain invalid characters or exceed length limits?
  - System validates metadata before processing and returns validation error with specific field issues

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept document uploads via API endpoint supporting three file formats: markdown (.md), plain text (.txt), and PDF (.pdf)

- **FR-002**: System MUST validate uploaded files before processing, rejecting invalid formats, empty files, and files exceeding maximum size limits with descriptive error messages

- **FR-003**: System MUST split document content into semantic chunks targeting 300-500 tokens, with strict sentence integrity requirement taking precedence over token limits (chunks may exceed target range to preserve complete sentences; no mid-sentence splits allowed)

- **FR-004**: System MUST generate semantic representations for each chunk to enable similarity-based search and retrieval

- **FR-005**: System MUST store chunks with associated metadata including: source filename, subject tag (selected from predefined list managed in database/config), chunk index (sequential position in original document), and ingestion timestamp

- **FR-006**: System MUST prevent duplicate ingestion by detecting when the exact same document content has already been processed using SHA-256 hash of normalized content (whitespace/line endings stripped) for idempotent operation

- **FR-007**: System MUST return an ingestion summary response containing: unique document identifier, number of chunks created, total ingestion time in milliseconds, and skip indicator if duplicate

- **FR-008**: System MUST make ingested content immediately queryable via the existing query endpoint without requiring cache refresh or index rebuild delays

- **FR-009**: System MUST implement global quota management for rate limiting, queuing all ingestion requests fairly when the 15 RPM API limit is reached, ensuring no single upload monopolizes the quota and all queued requests complete as quota resets. Automatic retry with exponential backoff applies for transient errors

- **FR-010**: System MUST roll back any partially created chunks if retry attempts are exhausted, ensuring no corrupted or incomplete data persists in the knowledge base

- **FR-011**: System MUST support concurrent uploads from multiple administrators without data corruption or race conditions

- **FR-012**: System MUST extract plain text from PDF files for chunk creation (advanced layout analysis and formatting preservation are out of scope for v1)

- **FR-013**: System MUST validate and sanitize subject metadata tags before storage, rejecting invalid characters or excessive length

### Non-Functional Requirements

#### Observability & Monitoring

- **Logging**: System MUST produce structured JSON logs for all ingestion operations containing the following fields:
  - `request_id`: Unique identifier for tracing a single upload request through the system
  - `document_id`: Identifier for the document being processed
  - `filename`: Original filename for correlation
  - `chunks_created`: Count of chunks successfully created
  - `ingestion_time_ms`: Total time from upload start to completion in milliseconds
  - `rate_limit_queue_time`: Time spent waiting in rate limit queue (milliseconds)
  - `error_message`: Detailed error information for failures (if applicable)
  - `timestamp`: ISO 8601 timestamp for temporal analysis

- **Metrics**: System MUST expose application-level metrics for operational visibility:
  - **Throughput**: Documents processed per hour (aggregated counter)
  - **Error Rate**: Percentage of failed ingestions (ratio of failures to total attempts)
  - **Average Ingestion Latency**: Mean processing time in milliseconds (p50, p95, p99)
  - **Rate Limit Queue Depth**: Current count of requests waiting for API quota availability

- **Tracing**: Distributed tracing with OpenTelemetry spans is explicitly deferred to v2. V1 relies on structured logging with correlation via `request_id` for troubleshooting

### Key Entities

- **Document**: Represents an uploaded file containing educational content. Key attributes include unique identifier, original filename, file format (markdown/txt/pdf), subject tag, total size in bytes, ingestion timestamp, and processing status.

- **Chunk**: Represents a semantic segment of a document optimized for retrieval. Key attributes include unique identifier, parent document identifier, sequential index within document, text content (300-500 tokens), semantic representation for search, and metadata inherited from parent document (subject, source filename).

- **Ingestion Result**: Represents the outcome of an upload operation. Attributes include document identifier, success/failure status, chunks created count, processing time in milliseconds, skip indicator for duplicates, and error details if failed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Content administrators can upload a 3000-word markdown file and receive confirmation of successful ingestion in under 10 seconds

- **SC-002**: Uploaded content is immediately queryable by learners through the existing query endpoint with zero delay after ingestion completes

- **SC-003**: All chunks maintain sentence integrity with no mid-sentence splits, ensuring readable and coherent search results

- **SC-004**: When the same file is uploaded twice, the system prevents duplicate chunks - the second upload returns a skip indicator with zero new chunks created

- **SC-005**: Metadata (source filename, subject tag, chunk index) is correctly stored and returned for 100% of chunks when queried

- **SC-006**: Large documents requiring 20+ semantic processing calls complete successfully despite rate limits through automatic throttling and retry mechanisms

- **SC-007**: Failed uploads with exhausted retries leave zero partial or corrupted chunks in the knowledge base (complete rollback verification)

- **SC-008**: Content administrators receive clear, actionable error messages for all failure scenarios (invalid format, size exceeded, corrupted file, etc.)

### Performance & UX Targets

- **Page Load**: N/A for backend-only API

- **API Performance**: 
  - Ingestion endpoint completes for 3000-word markdown file in <10 seconds (p95)
  - Validation and duplicate detection occurs in <500ms before processing begins
  - Ingestion summary response returns immediately after processing completes (no polling required)

- **Accessibility**: N/A for backend-only API

- **Responsive Design**: N/A for backend-only API

## Assumptions

1. **Duplicate Detection Method**: Duplicate detection uses SHA-256 hash of normalized content (whitespace/line endings stripped) to prevent false negatives from formatting differences while maintaining collision resistance. Renamed files with identical normalized content are recognized as duplicates

2. **Chunk Size Rationale**: Chunking algorithm prioritizes sentence integrity (never splits mid-sentence). Token count targets (300-500 tokens) are soft caps; chunks may exceed this range if needed to preserve complete sentences. Range is based on typical retrieval window sizes that balance context completeness with precision

3. **PDF Text Extraction**: Assumes standard, searchable PDFs with selectable text; scanned PDFs requiring OCR are out of scope for v1

4. **Subject Tags**: Subject tags are managed as a predefined list (e.g., Biology, History, Mathematics, Physics). Content administrators select from this list during upload via dropdown UI. The list is maintained in database/config and can be extended by administrators without code changes. This prevents inconsistency from free-form entry (e.g., "bio" vs "biology")

5. **Rate Limiting Strategy**: Rate limiting operates at the system level (global quota of 15 RPM for Gemini API). When limit is reached, all pending ingestion requests are queued fairly. No single upload monopolizes the API. The system completes all queued ingestions eventually as quota resets. This ensures fair distribution across concurrent uploads and prevents starvation

6. **Retry Strategy Parameters**: Assumes exponential backoff starts at 1 second with 2x multiplier, maximum 5 retry attempts before rollback (configurable in implementation)

7. **Rate Limit Handling**: Assumes semantic processing service provides rate limit feedback in responses, enabling smart throttling

8. **Concurrent Upload Limit**: Assumes system can handle up to 10 concurrent uploads without degradation; higher loads may require queueing

9. **File Size Limits**: Assumes maximum file size of 10MB per upload to prevent resource exhaustion; larger documents should be split by administrator

10. **Metadata Constraints**: Assumes subject tags are limited to 50 characters, filenames limited to 255 characters (standard filesystem limits)

11. **Observability Strategy**: Assumes observability is achieved through structured logging with request/document correlation IDs and application-level metrics (throughput, error rates, latency percentiles, queue depth). Distributed tracing is deferred to v2. Logs use JSON format for machine parsing

## Out of Scope

The following capabilities are explicitly excluded from this feature and may be considered for future iterations:

- **PDF Layout Analysis**: Advanced parsing of tables, columns, images, and complex formatting in PDFs - only plain text extraction supported in v1

- **Batch Upload**: Uploading multiple files in a single API request - administrators must upload files individually

- **Document Versioning**: Tracking updates to previously ingested documents or maintaining version history - each upload is treated as a new document

- **Document Deletion**: Removing documents or chunks from the knowledge base after ingestion - no deletion API in v1

- **Authentication & Authorization**: Access control for who can upload documents - assumes trusted administrator environment

- **Web Scraping**: Ingesting content directly from URLs or web pages - only file upload supported

- **OCR for Scanned PDFs**: Optical character recognition for image-based PDFs - requires searchable text PDFs only

- **Format Preservation**: Maintaining original document formatting (bold, italics, headings) in chunks - chunks are plain text only

- **Custom Chunking Strategies**: Administrator-defined chunk sizes or splitting rules - system uses fixed 300-500 token strategy

- **Ingestion Progress Tracking**: Real-time progress updates for long-running uploads - response returns only after completion

- **Content Preview**: Viewing or validating chunks before final ingestion - no preview or confirmation step
