# CourseFlow Constitution

## Project Identity

- **Name**: CourseFlow
- **Type**: AI-Powered Knowledge Q&A System (RAG-based)
- **Scope**: Domain-agnostic learning assistant supporting any subject (programming, science, history, math, etc.)
- **Architecture**: API-first with FastAPI, hexagonal architecture, async/await native
- **Constraint**: Zero-cost architecture using free-tier services (Gemini, ChromaDB, SQLite)
- **Purpose**: Portfolio/demo project showcasing AI engineering and system design capabilities

---

## Core Principles

### I. Code Quality Standards

All code in the CourseFlow project MUST adhere to the following non-negotiable standards:

- **Clean Code**: Code MUST be self-documenting with clear variable/function names that reveal intent. Comments explain "why", not "what".
- **Maintainability**: Functions MUST do one thing well (Single Responsibility). Maximum function length: 50 lines. Maximum file length: 500 lines. Violations require explicit justification.
- **Documentation**: Every public API, module, and complex algorithm MUST have documentation explaining purpose, parameters, return values, and usage examples.
- **Code Reviews**: All code changes MUST pass peer review before merge. Reviewers verify adherence to these standards.
- **Static Analysis**: Code MUST pass linting and static analysis tools with zero errors. Warnings MUST be addressed or explicitly suppressed with justification.
  - **Tools**: `ruff` for linting/formatting, `mypy --strict` for type checking
  - **Pre-commit Hooks**: Automatic formatting and validation before commit
- **DRY Principle**: Code duplication beyond 3 lines MUST be refactored into reusable functions/modules.

**Rationale**: Maintainable code reduces technical debt, accelerates onboarding, and minimizes bugs. Clear standards prevent subjective debates during reviews.

---

### II. Testing Standards

Testing is mandatory and follows a structured approach:

- **Test-First Development**: For complex features, tests MUST be written before implementation (Red-Green-Refactor). Tests verify requirements first, then implementation makes them pass.
- **Unit Tests**: All business logic MUST have unit test coverage. Minimum coverage threshold: 80% for new code. Pure functions and critical paths require 100% coverage.
- **Integration Tests**: API endpoints, database interactions, and inter-service communication MUST have integration tests validating contracts and data flow.
- **Test Organization**: Tests MUST be organized in three categories:
  - `tests/unit/` - Fast, isolated, no external dependencies
  - `tests/integration/` - Database, API, service interactions
  - `tests/e2e/` - RAG pipeline end-to-end tests (query → retrieval → generation)
- **Test Quality**: Tests MUST be deterministic (no flaky tests), independent (no shared state), and fast (unit tests <100ms, integration tests <5s).
- **Continuous Testing**: All tests MUST pass in CI/CD before merge. Broken tests block all deployments.

**RAG-Specific Testing Requirements** (NEW):
- **Golden Dataset**: MUST maintain 10-20 test question-answer pairs covering multiple subjects
- **Retrieval Quality**: Golden dataset tests MUST validate retrieval precision >70% (correct docs in top-5)
- **Retrieval Scores**: Top-1 similarity score MUST be >0.7 (cosine similarity)
- **Answer Quality**: LLM responses MUST contain expected keywords from golden dataset
- **Latency Tests**: E2E RAG query tests MUST complete in <3 seconds (p95)
- **Token Tracking**: Tests MUST verify token consumption is logged for every LLM call

**Rationale**: Comprehensive testing catches bugs early, documents expected behavior, and enables confident refactoring. Test-first ensures features are designed for testability. RAG systems have unique quality metrics (retrieval precision, semantic relevance) that require specialized testing.

---

### III. AI Engineering Standards (NEW)

CourseFlow is an AI-powered system and MUST adhere to AI-specific best practices:

#### LLM Integration

- **Provider Abstraction**: LLM client MUST use Port & Adapter pattern (interface-based design) to enable swapping providers (Gemini ↔ OpenAI ↔ Ollama) without changing domain logic
- **Streaming Support**: All LLM calls MUST support streaming responses (Server-Sent Events) for better UX
  - Initial implementation MAY be non-streaming, but architecture MUST accommodate future streaming
- **Error Handling**: API errors MUST be handled gracefully:
  - **Rate Limits (429)**: Exponential backoff retry (1s, 2s, 4s, max 3 retries)
  - **Quota Exceeded**: Return HTTP 429 with `retry_after` header
  - **Network Failures**: Log error, return cached response or friendly error message
  - **Hallucination Prevention**: MUST include retrieved context in prompts to ground responses
- **Fallback Strategy**: If primary LLM fails after retries, MUST return cached response or structured error (no crashes)

#### Token Management

- **Budget Tracking**: Every LLM call MUST log token consumption:
  - Prompt tokens (input)
  - Completion tokens (output)
  - Total tokens
  - Timestamp, model used, request_id
- **Context Window Limits**: MUST validate total tokens < model limit before API call
  - Gemini 1.5 Flash: 1M token context (but keep practical limit at 8K for cost)
  - MUST trim conversation history or retrieved context if exceeding limit
- **Cost Monitoring**: MUST emit metrics for daily/monthly token usage
  - Even in free tier, track to demonstrate cost awareness
  - Metrics: tokens/day, tokens/query (avg, p95), queries/day
- **Token Optimization**:
  - MUST trim conversation history to last 5 turns max
  - MUST limit retrieved context to top 5 chunks (configurable)
  - MUST use efficient prompts (no redundant instructions)

#### RAG Pipeline Standards

- **Retrieval Quality**: MUST retrieve semantically relevant documents
  - Minimum cosine similarity threshold: 0.7
  - Top-k configurable (default: 5)
  - MUST log retrieval scores for monitoring
- **Context Construction**: MUST format retrieved chunks clearly for LLM:
  ```
  Context from knowledge base:
  [Source: python-async.md]
  Content: "To create async functions, use async def..."
  
  [Source: python-events.md]
  Content: "Event loops manage async tasks..."
  
  Question: {user_query}
  ```
- **Chunk Size**: Document chunks MUST be 300-500 tokens
  - Balance: Smaller chunks = more precise retrieval, larger chunks = more context
  - MUST NOT split mid-sentence (respect paragraph boundaries)
- **Embedding Caching**: MUST cache embeddings locally to minimize API calls
  - ChromaDB handles persistence automatically
  - MUST NOT re-embed same content
- **Retrieval Metrics**: MUST track and log:
  - Retrieval latency (p50, p95, p99)
  - Average similarity score
  - Number of chunks retrieved per query

#### Quota & Rate Limiting

- **Respect Free Tier**: Gemini free tier limits MUST be enforced
  - 15 requests/minute (RPM)
  - 1,500 requests/day
  - 1M tokens/minute (TPM)
- **Client-Side Rate Limiting**: MUST implement request tracking:
  - Track timestamps of last N requests
  - Block new requests if RPM limit reached
  - Return HTTP 429 with `retry_after` header
- **Quota Exceeded Handling**:
  - MUST detect quota errors from API response
  - MUST log quota exceeded events
  - MUST return actionable error: "Gemini API quota exceeded. Try again in 60 seconds."
- **Graceful Degradation**: If quota exceeded:
  - Option 1: Return cached/pre-computed responses
  - Option 2: Suggest retry time
  - Option 3: (Future) Fall back to local LLM (Ollama)
  - MUST NOT crash or return generic 500 error

**Rationale**: AI systems have unique failure modes (quota limits, rate limits, hallucinations, token budget overflow). Proper engineering prevents costly mistakes, ensures reliability, and demonstrates production-ready thinking for portfolio/interviews.

---

### IV. Architecture & Tech Stack (NEW)

#### Mandatory Technologies

**API & Application Layer:**
- **API Framework**: FastAPI 0.109+ (async/await native, automatic OpenAPI docs, Pydantic validation)
- **Python Version**: 3.11+ (required for improved async performance and type hints)
- **HTTP Client**: httpx (async HTTP client for LLM API calls)

**AI/ML Stack:**
- **LLM Provider**: Google Gemini 1.5 Flash API (free tier: 15 RPM, 1M TPM)
- **Embeddings**: Gemini text-embedding-004 (free tier, 768 dimensions)
- **Vector Database**: ChromaDB 0.4.22+ (local, persistent to `./data/chroma`)
  - MUST use cosine similarity metric
  - MUST persist data locally (no in-memory mode)

**Data Layer:**
- **Database**: SQLite with aiosqlite (local, `./data/courseflow.db`)
  - Stores: conversation history, user queries, metadata
  - MUST use async queries (aiosqlite)
- **Caching**: (Optional) Redis for response caching in future phases

**Development Tools:**
- **Linting**: ruff (replaces flake8, black, isort)
- **Type Checking**: mypy --strict
- **Testing**: pytest + pytest-asyncio + pytest-cov
- **Package Management**: uv or poetry (fast dependency resolution)

#### Architecture Patterns

- **Hexagonal Architecture (Ports & Adapters)**: Domain logic isolated from infrastructure
  - **Domain Layer**: Pure business logic (no framework dependencies)
  - **Application Layer**: Use cases (RAG service, ingestion service)
  - **Infrastructure Layer**: Adapters (Gemini client, ChromaDB, SQLite)
  - **API Layer**: FastAPI routes (thin controllers)
- **Dependency Injection**: FastAPI `Depends()` for service lifecycle management
  - Services initialized once per request
  - Easy to mock for testing
- **Async First**: All I/O operations (DB, API, file) MUST use async/await
  - No blocking calls in request handlers
  - Use `asyncio.gather()` for concurrent operations
- **Type Safety**: 
  - Pydantic models for all API requests/responses
  - `mypy --strict` enforcement (no `Any` types without explicit annotation)
  - Type hints for all function signatures

#### Project Structure (Enforced)

```
courseflow/
├── src/courseflow/
│   ├── domain/              # Business logic (LLM-agnostic)
│   │   ├── models.py        # Core data models (Query, Document, etc.)
│   │   ├── ports.py         # Interfaces (VectorStorePort, LLMPort)
│   │   └── exceptions.py    # Custom exceptions
│   ├── application/         # Use cases
│   │   ├── rag_service.py   # RAG query orchestration
│   │   └── ingestion_service.py  # Document ingestion
│   ├── infrastructure/      # Adapters (external dependencies)
│   │   ├── llm/
│   │   │   └── gemini.py    # Gemini API client
│   │   ├── vector_store/
│   │   │   └── chroma.py    # ChromaDB adapter
│   │   ├── embeddings/
│   │   │   └── gemini.py    # Gemini embeddings
│   │   └── repositories/
│   │       └── conversation_repo.py  # SQLite conversation storage
│   ├── api/                 # FastAPI routes
│   │   ├── main.py          # App initialization
│   │   ├── routes/
│   │   │   ├── query.py     # Query endpoints
│   │   │   └── health.py    # Health check
│   │   └── dependencies.py  # DI setup
│   └── config.py            # Settings (Pydantic BaseSettings)
├── tests/
│   ├── unit/                # Isolated tests (domain, mocks)
│   ├── integration/         # API + DB tests
│   ├── e2e/                 # Full RAG pipeline tests
│   └── fixtures/            # Test data (golden dataset)
├── data/                    # Local data (gitignored)
│   ├── chroma/              # ChromaDB persistence
│   └── courseflow.db        # SQLite database
├── docs/                    # Knowledge base documents
│   ├── programming/
│   ├── biology/
│   └── history/
├── scripts/                 # Utility scripts
│   └── ingest_docs.py       # Bulk document ingestion
├── pyproject.toml           # Dependencies, tool configs
├── .env.example             # Environment variable template
└── README.md
```

**Rationale**: Consistent structure improves onboarding. Hexagonal architecture enables testing without external dependencies. Clear separation of concerns makes code maintainable and prevents coupling.

---

### V. Performance Requirements

All features MUST meet performance benchmarks before production deployment:

#### API Response Time

- **RAG Query Endpoint**: 95th percentile MUST be <2 seconds (end-to-end)
  - Breakdown target:
    - Embedding generation: <300ms
    - Vector search: <200ms
    - LLM generation (first token): <1000ms
    - Total overhead: <500ms
- **Health Check**: MUST respond in <100ms
- **Document Ingestion**: MUST process 1000-word document in <5 seconds

#### Retrieval Performance

- **Vector Search Latency**: ChromaDB local search MUST complete in <200ms for 10K documents
- **Embedding Caching**: MUST cache embeddings to avoid redundant API calls
  - Cache hit rate target: >80% for repeated queries
- **Concurrent Queries**: MUST handle 5 concurrent RAG queries without degradation
  - Rate limiting may reduce throughput, but latency MUST stay <2s

#### LLM Generation

- **First Token Latency**: Streaming mode MUST deliver first token in <1 second
- **Throughput**: MUST generate 20-30 tokens/second (Gemini 1.5 Flash baseline)

#### Database Performance

- **All Queries Indexed**: No full table scans allowed
- **Query Review**: Execution plans reviewed for queries >100ms
- **Connection Pooling**: SQLite MUST use connection pooling (aiosqlite handles this)

#### Resource Usage

- **Memory**: Application MUST run in <512MB RAM (excluding vector DB)
- **Disk**: ChromaDB index MUST be <100MB for 10K document chunks
- **CPU**: MUST NOT exceed 50% CPU usage during steady-state queries

#### Monitoring & Metrics

- **Logging**: MUST log response times for every query
  - Structured logs with: `request_id`, `latency_ms`, `token_count`, `retrieval_score`
- **Metrics Exported**: MUST expose metrics endpoint (`/metrics`) with:
  - Query count (total, success, error)
  - Latency histogram (p50, p95, p99)
  - Token consumption (per query, per day)
  - Gemini API quota status

#### Performance Testing

- **Load Tests**: MUST validate 10 concurrent users (pytest-asyncio)
- **Latency Tests**: MUST run against golden dataset and measure p50/p95/p99
- **Regression Tests**: Performance MUST NOT degrade >10% between releases

**Rationale**: Performance directly impacts user satisfaction. Slow RAG systems are unusable. <2s response time ensures interactive UX. Monitoring prevents performance degradation over time.

---

### VI. Zero-Cost Constraints (NEW)

This is a portfolio/demo project with **ZERO recurring cloud costs**:

#### Mandatory Free Tier Usage

- **LLM API**: Google Gemini free tier ONLY
  - 15 requests/minute
  - 1,500 requests/day
  - 1M tokens/minute
  - MUST NOT use paid OpenAI API (unless explicitly switching for comparison)
- **Vector DB**: ChromaDB local ONLY
  - MUST persist to local disk (`./data/chroma`)
  - MUST NOT use hosted Pinecone, Weaviate, etc.
- **Database**: SQLite local ONLY
  - MUST persist to local disk (`./data/courseflow.db`)
  - MUST NOT use hosted PostgreSQL, MySQL, etc.
- **Hosting**: Local development ONLY
  - MUST NOT deploy to paid cloud services (AWS, GCP, Azure)
  - Future deployment: Free tier options (Render, Fly.io, Railway free plans)

#### Cost Monitoring & Alerts

- **Quota Tracking**: MUST log Gemini API usage:
  - Requests per minute (current window)
  - Requests per day (rolling 24h)
  - Tokens consumed per day
- **Alerts**: MUST warn when approaching limits:
  - 90% of daily request quota (1350/1500)
  - 90% of minute quota (13/15)
- **Dashboard**: MUST expose usage stats via `/metrics` endpoint

#### Fallback Plan (Future Phase)

If Gemini quota consistently exceeded:
- **Option 1**: Implement caching (Redis) to serve repeated queries
- **Option 2**: Deploy local LLM (Ollama + Llama 3.2 3B)
  - Trade-off: Slower inference, no API cost
- **Option 3**: Queue requests to stay within quota
  - Trade-off: Increased latency, better reliability

#### Trade-offs Explicitly Accepted

- ✅ **15 RPM Limit**: Acceptable for demo/portfolio use case
  - Showcases rate limiting implementation
- ✅ **Local Data Only**: No cloud backup
  - Acceptable for non-production system
- ✅ **Single-User Deployment**: No multi-tenancy
  - Simplifies architecture, sufficient for demo
- ✅ **No Commercial Usage**: Free tier restriction
  - Clearly documented in README
- ❌ **No Production SLA**: Gemini free tier has no uptime guarantee
  - Not suitable for real production workload

**Rationale**: Zero-cost architecture demonstrates:
1. System design skills (abstraction, hexagonal architecture)
2. Cost optimization thinking (quota management, caching strategies)
3. Engineering pragmatism (accepting trade-offs)
4. Production-ready patterns (rate limiting, monitoring) without production costs

This is valuable for portfolio/interviews where demonstrating skills matters more than scale.

---

### VII. Domain-Agnostic Design (NEW)

CourseFlow MUST support **ANY subject area** (not just programming):

#### Generic Data Models

- **Document Model**: MUST NOT assume subject-specific fields
  - ❌ Avoid: `language`, `framework`, `programming_concept`
  - ✅ Use: `subject`, `topic`, `difficulty`, `tags`
- **Metadata Schema**:
  ```python
  {
    "subject": "biology" | "programming" | "history" | "math",
    "topic": "photosynthesis" | "async-await" | "world-war-2",
    "difficulty": "beginner" | "intermediate" | "advanced",
    "source": "textbook" | "tutorial" | "research-paper",
    "tags": ["plants", "energy"] | ["python", "concurrency"]
  }
  ```
- **Query Processing**: MUST NOT hardcode subject-specific terminology
  - Generic prompt templates work for any subject

#### Multi-Subject Knowledge Base

**Supported Subjects** (for testing):
- **Programming**: Python tutorials, JavaScript guides, async/await concepts
- **Science**: Biology (photosynthesis, mitosis), Physics (Newton's laws), Chemistry
- **History**: World War II, Ancient Rome, Industrial Revolution
- **Math**: Calculus (derivatives, integrals), Linear Algebra (matrices, eigenvalues)

**Knowledge Base Structure**:
```
docs/
├── programming/
│   ├── python-async.md
│   ├── python-functions.md
│   └── javascript-promises.md
├── biology/
│   ├── photosynthesis.md
│   ├── mitosis.md
│   └── cell-structure.md
├── history/
│   ├── world-war-2.md
│   └── ancient-rome.md
└── math/
    ├── calculus-derivatives.md
    └── linear-algebra-matrices.md
```

#### Subject-Agnostic Prompts

**Generic System Prompt Template**:
```
You are a knowledgeable tutor helping students learn {subject}.
Answer questions based ONLY on the provided context from educational materials.
If the context doesn't contain enough information, say so clearly.

Context:
{retrieved_chunks}

Question: {user_query}

Provide a clear, accurate answer with examples when possible.
```

**Subject Detection** (Optional):
- Can infer subject from metadata of retrieved documents
- Can allow user to specify subject in query: `{"query": "...", "subject": "biology"}`

#### Testing Across Subjects

- **Golden Dataset**: MUST include questions from at least 3 different subjects
- **Cross-Subject Tests**: Verify query "What is photosynthesis?" doesn't retrieve programming docs
- **Metadata Filtering**: (Future) Support filtering by subject: `{"query": "...", "filter": {"subject": "programming"}}`

**Rationale**: Domain-agnostic design:
1. Makes the system more versatile (real-world applicability)
2. Demonstrates broader engineering thinking (not just coding tutorials)
3. Showcases ability to build general-purpose platforms
4. Easier to extend to new subjects without code changes

---

### VIII. User Experience (API-First)

Since CourseFlow v1 is **API-first** (no web UI), UX focuses on API design:

#### API Design Standards

- **RESTful Conventions**: Standard HTTP methods and status codes
  - `POST /api/v1/query` - Submit question
  - `GET /api/v1/health` - Health check
  - `POST /api/v1/ingest` - (Future) Upload documents
- **Consistent Response Structure**: All responses MUST follow same JSON schema:
  ```json
  {
    "success": true,
    "data": {
      "answer": "...",
      "sources": ["doc1.md", "doc2.md"],
      "retrieval_count": 3
    },
    "metadata": {
      "request_id": "req_abc123",
      "timestamp": "2025-02-07T12:34:56Z",
      "latency_ms": 1234,
      "token_count": 567
    },
    "error": null
  }
  ```
- **Error Responses**: MUST be actionable and clear
  - ✅ Good: `{"error": "quota_exceeded", "message": "Gemini API quota exceeded (15 RPM). Retry after 60 seconds.", "retry_after": 60}`
  - ❌ Bad: `{"error": "Error 429"}`
- **HTTP Status Codes**:
  - `200 OK` - Success
  - `400 Bad Request` - Invalid input (e.g., empty query)
  - `429 Too Many Requests` - Rate limit exceeded
  - `500 Internal Server Error` - Unexpected failure
  - `503 Service Unavailable` - Downstream service down (Gemini API)

#### OpenAPI Documentation

- **Auto-Generated Docs**: FastAPI MUST generate OpenAPI spec
  - Available at `/docs` (Swagger UI)
  - Available at `/redoc` (ReDoc)
- **Documentation Quality**:
  - All endpoints MUST have descriptions
  - All request/response models MUST have example values
  - All error codes MUST be documented

#### API Usability

- **Default Values**: Sensible defaults for optional parameters
  - `max_results`: 5
  - `temperature`: 0.7
- **Validation**: Pydantic MUST validate all inputs
  - Provide clear error messages for validation failures
  - Example: `{"error": "validation_error", "details": {"query": "Field required"}}`
- **Idempotency**: GET requests MUST be idempotent (same query = same result, if cached)

#### Future UI Principles (Deferred to v2)

When web UI is added:
- Adopt **WCAG 2.1 AA** accessibility standards
- Implement **responsive design** (mobile, tablet, desktop)
- Use consistent **design system** (colors, typography, components)
- Show **loading states** for operations >200ms
- Provide **error recovery** (retry buttons, helpful messages)

**Rationale**: API-first allows focus on core RAG functionality without UI complexity. Well-designed APIs are easier to test and consume. UI can be added later with proper UX investment.

---

## Development Workflow

### Code Review Requirements

- All pull requests MUST be reviewed by at least one team member (or self-review with checklist for solo projects)
- Reviewers MUST verify compliance with all core principles:
  - ✅ Code quality (clean code, documentation)
  - ✅ Testing (coverage, quality)
  - ✅ AI engineering (token tracking, error handling)
  - ✅ Architecture (hexagonal pattern, async/await)
  - ✅ Performance (latency benchmarks)
- Automated checks MUST pass before human review:
  - `pytest` - All tests pass
  - `ruff check` - No linting errors
  - `mypy --strict` - No type errors
  - `pytest-cov` - Coverage >80%
- Review checklist includes:
  - Does this change respect zero-cost constraints?
  - Are API errors handled gracefully?
  - Is token usage logged?
  - Are new features tested with golden dataset?

### Quality Gates

Before merging to main branch:

1. **Tests**: All tests pass (unit, integration, e2e RAG tests)
2. **Coverage**: Code coverage meets thresholds (80% overall, 100% for critical RAG pipeline)
3. **Linting**: Static analysis passes (ruff, mypy)
4. **Performance**: Benchmarks met (p95 latency <2s for RAG queries)
5. **AI Metrics**: Token usage logged (no missing metrics)
6. **Documentation**: Updated (API docs, inline comments, README)
7. **Golden Dataset**: If changing RAG logic, golden tests MUST still pass

### Breaking Changes

- Breaking changes MUST be discussed in design review before implementation
- Migration plan MUST be documented
- Backward compatibility maintained when possible
- Version bump following semantic versioning (MAJOR.MINOR.PATCH)

### CI/CD Pipeline (GitHub Actions)

**On every push/PR**:
```yaml
- Install dependencies (uv/poetry)
- Run linting (ruff check)
- Run type checking (mypy --strict)
- Run tests (pytest -v --cov)
- Check coverage threshold (80%)
- Build Docker image (optional)
```

**On merge to main**:
```yaml
- Tag release (semantic versioning)
- Generate changelog
- Deploy to staging (if applicable)
```

---

## Governance

This constitution defines the fundamental engineering standards for CourseFlow. All development practices, code reviews, and architectural decisions MUST align with these principles.

### Amendment Process

1. **Proposal**: Proposed changes MUST be documented with:
   - Rationale (why is this change needed?)
   - Impact analysis (what code/processes are affected?)
   - Migration plan (how to transition existing code?)
2. **Discussion**: Team discussion and consensus required (>75% approval for solo projects, document decision rationale)
3. **Version Bump**: Following semantic versioning:
   - **MAJOR (X.0.0)**: Principle removal or incompatible governance changes
   - **MINOR (x.Y.0)**: New principle added or existing principle significantly expanded
   - **PATCH (x.y.Z)**: Clarifications, wording improvements, non-semantic fixes
4. **Migration**: Migration plan created for affected code/processes
5. **Documentation**: Templates and documentation updated to reflect changes

### Enforcement

- All pull requests MUST reference this constitution in review process
- Violations MAY be accepted with explicit justification and technical debt ticket
  - Example: "Exceeding 50-line function limit due to complex RAG orchestration logic. Refactoring tracked in issue #123."
- Unjustified complexity or standard violations MUST be rejected
- Team retrospectives review constitution relevance and effectiveness quarterly

### Version Control

**Version**: 2.0.0  
**Ratified**: 2025-02-07  
**Last Amended**: 2025-02-07  
**Next Review**: TBD (or quarterly for active projects)

### Change Log

**v2.0.0 (2025-02-07)**:
- ✨ Added Section III: AI Engineering Standards
- ✨ Added Section IV: Architecture & Tech Stack
- ✨ Added Section VI: Zero-Cost Constraints
- ✨ Added Section VII: Domain-Agnostic Design
- 🔧 Modified Section V: Performance Requirements (API-first metrics)
- 🔧 Simplified Section VIII: User Experience (API-first focus)
- ✅ Enhanced Section II: Testing Standards (RAG-specific tests)

**v1.0.0 (2025-02-07)**:
- 🎉 Initial constitution with Code Quality, Testing, UX, Performance principles

---

**END OF CONSTITUTION**
