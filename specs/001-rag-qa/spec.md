# Feature Specification: Basic RAG Question Answering

**Feature Branch**: `001-rag-qa`  
**Created**: 2025-01-17  
**Status**: Draft  
**Input**: User description: "Feature: Basic RAG Question Answering (Zero-Cost, Domain Agnostic)"

## Clarifications

### Session 2025-01-17

- Q: How should the system handle Gemini API failures (timeout or unavailability)? → A: Retry once after 2-second timeout, then return error with categorization (API down vs. timeout)
- Q: How many documents should vector search retrieve (k value)? → A: k=3 (retrieve the top 3 most similar documents)
- Q: Should k value be fixed or dynamically adjusted based on query? → A: Fixed k=3 for all queries (simplest, most predictable)
- Q: Should vector search use a minimum similarity threshold to filter results? → A: Yes, require minimum similarity threshold of 0.5
- Q: How should the system respond when no documents are found above the similarity threshold? → A: Return error message "No relevant information found in knowledge base"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single-Turn Question Answering (Priority: P1)

A learner studying any subject wants to ask a single question about content in the knowledge base and receive an AI-generated answer based on that content.

**Why this priority**: This is the core value proposition - enabling learners to get answers from their study materials. Without this, there's no functional product.

**Independent Test**: Can be fully tested by sending a POST request with a text query and verifying that a relevant answer is returned within 3 seconds. Delivers immediate learning support value.

**Acceptance Scenarios**:

1. **Given** a knowledge base containing biology documents, **When** a learner submits the query "What is photosynthesis?", **Then** the system returns an answer explaining photosynthesis based on the knowledge base content
2. **Given** a knowledge base containing Python programming documents, **When** a learner submits the query "How to use async/await?", **Then** the system returns an answer explaining async/await syntax and usage based on the knowledge base content
3. **Given** a knowledge base with mixed subject content, **When** a learner asks a subject-specific question, **Then** the system retrieves and generates an answer using only relevant documents from that subject domain
4. **Given** any valid question, **When** the system processes the query, **Then** the response is returned in under 3 seconds
5. **Given** a question about content that exists in the knowledge base, **When** the answer is generated, **Then** the answer includes specific information sourced from the knowledge base documents

---

### User Story 2 - Rate Limit Handling (Priority: P2)

A learner using the system during peak times wants to receive clear feedback when the free-tier API quota is exceeded, so they understand why their query wasn't processed.

**Why this priority**: Essential for user experience and preventing confusion, but not required for basic functionality. Users must understand system limitations.

**Independent Test**: Can be tested by simulating rapid queries exceeding 15 requests per minute and verifying that subsequent requests receive an error message explaining the quota limit.

**Acceptance Scenarios**:

1. **Given** the system has received 15 requests in the current minute, **When** a learner submits query number 16, **Then** the system returns an error response indicating the quota limit has been exceeded
2. **Given** a rate limit has been exceeded, **When** the learner receives the error response, **Then** the message clearly explains the quota limit and suggests waiting before retrying
3. **Given** a new minute window has started, **When** the learner retries their query after a rate limit error, **Then** the system processes the query successfully

---

### User Story 3 - Empty or Irrelevant Query Handling (Priority: P3)

A learner wants to understand when their question cannot be answered based on the available knowledge base, so they can refine their query or seek information elsewhere.

**Why this priority**: Improves user experience but is less critical than core query functionality and rate limiting. Users can still get value even if edge cases aren't perfectly handled.

**Independent Test**: Can be tested by submitting queries with no relevant knowledge base content and verifying appropriate responses are returned.

**Acceptance Scenarios**:

1. **Given** a knowledge base about biology, **When** a learner asks "What is the capital of France?", **Then** the system returns a response indicating no relevant information was found in the knowledge base
2. **Given** any knowledge base, **When** a learner submits an empty query or query with only whitespace, **Then** the system returns an error indicating the query is invalid
3. **Given** a knowledge base, **When** a learner asks an extremely vague question like "Tell me something", **Then** the system attempts to provide a response based on available content or indicates the query is too broad
4. **Given** a knowledge base about biology, **When** a learner asks an unrelated question where no documents meet the 0.5 similarity threshold, **Then** the system returns the message "No relevant information found in knowledge base"

---

### Edge Cases

- What happens when the knowledge base is empty (no documents loaded)?
- How does the system handle queries exceeding reasonable length limits (e.g., >1000 characters)?
- **Gemini API Failure**: If the Gemini API is temporarily unavailable or returns an error, the system will retry once after a 2-second timeout. If the retry fails, return an error response categorizing the failure type (API unavailable vs. timeout exceeded).
- **Vector Search No Results Above Threshold**: When vector search returns no documents meeting the 0.5 similarity threshold, the system returns the error message "No relevant information found in knowledge base" without attempting to generate an answer.
- What happens if a query contains special characters, emojis, or non-English text?
- How does the system handle concurrent requests approaching the 15 RPM limit?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept text queries via an API endpoint
- **FR-002**: System MUST validate incoming queries are non-empty text strings
- **FR-003**: System MUST search the pre-populated knowledge base to find relevant documents matching the query intent by retrieving the top 3 most similar documents (k=3, fixed for all queries)
- **FR-003a**: System MUST filter vector search results using a minimum similarity threshold of 0.5 (documents below this threshold are excluded)
- **FR-004**: System MUST generate answers based on retrieved knowledge base content using an AI language model
- **FR-004a**: System MUST retry Gemini API calls once with a 2-second timeout if the initial call fails
- **FR-004b**: System MUST return a categorized error response (API unavailable vs. timeout) if the retry attempt fails
- **FR-005**: System MUST return answers as plain text in the response
- **FR-005a**: System MUST return the error message "No relevant information found in knowledge base" when vector search finds no documents above the 0.5 similarity threshold
- **FR-006**: System MUST track API quota usage to enforce the 15 requests per minute limit
- **FR-007**: System MUST return an error response with an explanatory message when the rate limit is exceeded
- **FR-008**: System MUST respond to valid queries within 3 seconds when the knowledge base is operational and AI service is responsive
- **FR-009**: System MUST operate with 10 pre-loaded documents in the knowledge base (ingestion not required)
- **FR-010**: System MUST support domain-agnostic queries (any subject area represented in the knowledge base)
- **FR-011**: System MUST operate in single-turn mode (no conversation history or multi-turn context)

### Key Entities

- **Query**: Represents a learner's question submitted to the system
  - Attributes: query text, timestamp, rate limit tracking metadata
  - Relationships: Maps to search results and generated answers

- **Knowledge Base Document**: Represents pre-loaded educational content
  - Attributes: document text/content, subject/domain metadata, document identifier
  - Relationships: Retrieved during search to answer queries

- **Answer**: Represents the AI-generated response
  - Attributes: answer text, source document references, generation timestamp
  - Relationships: Generated from Query and retrieved Knowledge Base Documents

- **Rate Limit Tracker**: Tracks API quota usage
  - Attributes: request count, time window, quota limits
  - Relationships: Monitors requests to enforce 15 RPM limit

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a learner submits the query "What is photosynthesis?" to a biology knowledge base, the system returns a relevant answer explaining photosynthesis
- **SC-002**: When a learner submits the query "How to use async/await?" to a Python programming knowledge base, the system returns a relevant answer explaining async/await
- **SC-003**: Generated answers include specific content sourced from the knowledge base documents (not generic information)
- **SC-004**: 90% of valid queries receive responses within 3 seconds under normal load conditions
- **SC-005**: When the quota limit is exceeded, learners receive a clear message explaining the limit has been reached and when they can retry their query
- **SC-006**: The system successfully handles queries from any subject domain represented in the 10 pre-loaded documents

### Performance & UX Targets

- **Page Load**: N/A (backend API only)
- **API Performance**: <3 seconds p95 for query responses, rate limiting enforced at exactly 15 requests per minute
- **Accessibility**: N/A (backend API only)
- **Responsive Design**: N/A (backend API only)

## Technical Constraints *(from project constitution)*

The following technical decisions are pre-determined by the project's architecture standards:

- **LLM**: Google Gemini 1.5 Flash API (free tier)
- **Embeddings**: Gemini text-embedding-004 (free tier)
- **Vector Database**: ChromaDB (local, persistent to ./data/chroma)
- **Database**: SQLite (local, ./data/courseflow.db)
- **API Framework**: FastAPI with async/await patterns
- **Rate Limiting**: Respect 15 RPM Gemini API limit

## Assumptions *(optional)*

- The 10 pre-loaded documents are already processed and indexed in the knowledge base before the system starts
- Documents are text-based and already prepared appropriately for search operations
- The Gemini 1.5 Flash free tier provides sufficient quota for initial testing and development
- Users understand this is a single-turn system (explicitly documented in the out-of-scope section)
- Network latency to Google's Gemini API is reasonable (<500ms average)
- The knowledge base documents are in English (multi-language support is not required in v1)

## Out of Scope *(optional)*

- Document ingestion, uploading, or management (assume 10 docs are pre-loaded)
- Multi-turn conversations or conversation history
- Streaming responses (answers returned in full after generation completes)
- User authentication, authorization, or user accounts
- Answer quality evaluation or feedback mechanisms
- Custom knowledge base selection (single shared knowledge base)
- Answer citations or source attribution in response format
- Query history or analytics
- Fine-tuning or customization of the Gemini model
- Support for non-text queries (images, audio, etc.)
