# Architecture Review: Document Ingestion Feature

**Reviewer**: Senior Architect (AI Agent)  
**Date**: 2025-02-12  
**Feature**: Document Ingestion and Knowledge Base Management  
**Phase**: Pre-Design Review (Phase 0 → Phase 1 Transition)

---

## Executive Summary

**Verdict**: ✅ **APPROVED with Minor Recommendations**

The proposed design for document ingestion aligns well with CourseFlow's hexagonal architecture and constitutional principles. The research demonstrates sound technical decision-making, proper dependency resolution, and adherence to zero-cost constraints.

**Key Strengths**:
- Strong alignment with hexagonal architecture (ports & adapters)
- Zero-cost constraint compliance (all dependencies local, no paid services)
- Async-first design (FastAPI native patterns)
- Clear separation of concerns (domain, application, infrastructure layers)

**Recommendations**:
1. Ensure domain layer remains LLM-agnostic (tiktoken in infrastructure, not domain)
2. Create explicit port interfaces for new adapters (PDFExtractorPort, ChunkerPort)
3. Add retry circuit breaker pattern to rate limiter (prevent cascading failures)

---

## Current Architecture Assessment

**Pattern Detected**: Hexagonal Architecture (Ports & Adapters)

**Existing Structure** (per project analysis):
```
src/courseflow/
├── domain/              ✅ Business logic (LLM-agnostic)
│   ├── models.py        
│   └── exceptions.py    
├── application/         ✅ Use cases (RAG orchestration)
│   └── rag_service.py   
├── infrastructure/      ✅ Adapters (external dependencies)
│   ├── llm/
│   │   └── gemini.py    
│   ├── embeddings/
│   │   └── gemini.py    
│   ├── vector_store/
│   │   └── chroma.py    
│   └── repositories/
│       └── query_repo.py
└── api/                 ✅ FastAPI routes (thin controllers)
    ├── main.py
    └── routes/
```

**Constitution Alignment**: ✅ **PASS**
- Hexagonal architecture properly implemented
- Async/await native (FastAPI)
- Clear layer boundaries
- No violations detected

---

## Proposed Design Review

### 1. Technology Choices

#### PyMuPDF 1.27.1 (PDF Extraction)
**Assessment**: ✅ **APPROVED**

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Performance | ⭐⭐⭐⭐⭐ | 0.12s extraction (6x faster than alternatives) |
| Zero-cost | ✅ | Fully local, no API calls |
| Maintainability | ⭐⭐⭐⭐ | Active development, stable API |
| Hexagonal fit | ✅ | Can be wrapped in `PDFExtractorPort` interface |

**Recommendation**: 
- Create `domain/ports.py` with `PDFExtractorPort` protocol:
  ```python
  from typing import Protocol
  
  class PDFExtractorPort(Protocol):
      async def extract_text(self, file_path: str) -> str:
          """Extract plain text from PDF file."""
          ...
  ```
- Implement `infrastructure/document_processing/pymupdf_extractor.py` adapter
- This enables future swap to pypdf or pdfplumber without domain changes

---

#### tiktoken 0.12.0 (Token Counting)
**Assessment**: ⚠️ **APPROVED with Caveat**

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Performance | ⭐⭐⭐⭐⭐ | 3-6x faster than alternatives |
| Zero-cost | ✅ | Fully local BPE tokenizer |
| Accuracy | ⭐⭐⭐⭐ | <5% mismatch with Gemini (acceptable) |
| Hexagonal fit | ⚠️ | **MUST NOT leak into domain layer** |

**Critical Recommendation**:
- ❌ **DO NOT import tiktoken in domain layer**
- ✅ **Create abstraction**:
  ```python
  # domain/ports.py
  class TokenCounterPort(Protocol):
      def count_tokens(self, text: str) -> int: ...
  
  # infrastructure/token_counting/tiktoken_counter.py
  class TiktokenCounter:
      def __init__(self):
          self.encoding = tiktoken.get_encoding("cl100k_base")
      
      def count_tokens(self, text: str) -> int:
          return len(self.encoding.encode(text))
  ```

**Rationale**: Domain layer must remain LLM-agnostic (Constitution III). If we later switch to Gemini's native token counting API or a different model, domain logic should be untouched.

---

#### NLTK 3.9.2 (Sentence Tokenization)
**Assessment**: ✅ **APPROVED**

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Accuracy | ⭐⭐⭐⭐⭐ | 98%+ sentence boundary detection |
| Performance | ⭐⭐⭐⭐ | <10ms for 1000 words |
| Zero-cost | ✅ | Local Punkt model (3MB) |
| Hexagonal fit | ✅ | Can be wrapped in `SentenceTokenizerPort` |

**Recommendation**:
- Create `infrastructure/text_processing/nltk_tokenizer.py` adapter
- Handle NLTK data download in application startup (not lazy load):
  ```python
  # api/main.py
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Startup: Download NLTK data
      import nltk
      nltk.download('punkt', quiet=True)
      yield
      # Shutdown: cleanup if needed
  
  app = FastAPI(lifespan=lifespan)
  ```

---

### 2. Architectural Patterns

#### Rate Limiting (In-Memory Queue + Exponential Backoff)
**Assessment**: ⚠️ **APPROVED with Enhancement**

**Proposed Pattern**:
```python
class RateLimiter:
    def __init__(self, requests_per_minute: int = 15):
        self.rpm = requests_per_minute
        self.requests = deque()  # [(timestamp, request_id), ...]
```

**Issues Identified**:
1. ⚠️ **No circuit breaker**: If Gemini API is down, requests will queue indefinitely
2. ⚠️ **Unbounded queue**: Memory leak risk if requests arrive faster than processing
3. ⚠️ **Lost on restart**: In-memory state lost on application restart (acceptable for v1)

**Recommendations**:
1. **Add circuit breaker pattern**:
   ```python
   from enum import Enum
   
   class CircuitState(Enum):
       CLOSED = "closed"  # Normal operation
       OPEN = "open"      # Failing, reject immediately
       HALF_OPEN = "half_open"  # Testing recovery
   
   class RateLimiter:
       def __init__(self, ...):
           ...
           self.circuit_state = CircuitState.CLOSED
           self.failure_count = 0
           self.last_failure_time = None
       
       async def acquire(self):
           if self.circuit_state == CircuitState.OPEN:
               if self._should_attempt_reset():
                   self.circuit_state = CircuitState.HALF_OPEN
               else:
                   raise CircuitOpenError("Rate limiter circuit open")
           
           # Proceed with normal rate limiting...
   ```

2. **Add max queue depth**:
   ```python
   MAX_QUEUE_DEPTH = 100  # From research open question
   
   async def acquire(self):
       if len(self.requests) >= MAX_QUEUE_DEPTH:
           raise QueueFullError("Ingestion queue full, try again later")
   ```

3. **Document v2 persistence plan**: Note in research.md that v2 should persist queue state to Redis for restart resilience

**Verdict**: ✅ Acceptable for v1 with enhancements

---

#### Chunking Algorithm (Sentence-Priority)
**Assessment**: ✅ **EXCELLENT**

**Proposed Algorithm**:
```
1. Split into sentences (NLTK)
2. Group sentences into chunks targeting 300-500 tokens
3. Sentence integrity ALWAYS preserved (can exceed 500 tokens)
4. No orphan sentences
```

**Strengths**:
- ✅ Directly implements clarified requirement (Q2)
- ✅ Deterministic (same input → same output)
- ✅ Testable (clear invariants to verify)
- ✅ Domain-focused (sentence = meaningful semantic unit)

**Architectural Fit**:
```python
# application/ingestion_service.py
class IngestionService:
    def __init__(
        self,
        chunker: ChunkerPort,  # Inject via port
        embedding_service: EmbeddingPort,
        ...
    ):
        self.chunker = chunker
        ...
    
    async def ingest_document(self, content: str, metadata: dict):
        chunks = self.chunker.create_chunks(content)
        # Orchestrate embedding, storage, etc.
```

**Verdict**: ✅ No changes needed

---

#### Duplicate Detection (SHA-256 Hashing)
**Assessment**: ✅ **APPROVED**

**Proposed Implementation**:
```python
def compute_content_hash(text: str) -> str:
    normalized = normalize_content(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
```

**Strengths**:
- ✅ Zero dependencies (stdlib)
- ✅ Collision-resistant (SHA-256)
- ✅ Fast (<1ms for 10K words)
- ✅ Normalization prevents false negatives

**Architectural Consideration**:
- Place in `domain/models.py` as `Document.compute_hash()` method (pure function, domain logic)
- Not infrastructure concern (no external dependency)

**Verdict**: ✅ No changes needed

---

### 3. Data Model & Schema

#### Proposed Entities (from research.md):

**Documents Table**:
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    content_hash TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    subject TEXT NOT NULL,
    ...
);
```

**Subjects Table**:
```sql
CREATE TABLE subjects (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    ...
);
```

**Assessment**: ✅ **GOOD with Minor Enhancement**

**Recommendations**:
1. **Add foreign key constraint**:
   ```sql
   CREATE TABLE documents (
       ...
       subject TEXT NOT NULL,
       FOREIGN KEY (subject) REFERENCES subjects(name) ON DELETE RESTRICT
   );
   ```
   This enforces referential integrity at DB level (defense in depth)

2. **Consider soft deletes** (for v2 audit trail):
   ```sql
   CREATE TABLE documents (
       ...
       deleted_at TEXT NULL,  -- ISO 8601 timestamp
   );
   ```
   Supports future document deletion feature (currently out of scope)

3. **Add ingestion metadata** (for observability):
   ```sql
   CREATE TABLE documents (
       ...
       ingestion_time_ms INTEGER NOT NULL,
       chunks_created INTEGER NOT NULL,
       created_at TEXT NOT NULL DEFAULT (datetime('now'))
   );
   ```

**Verdict**: ✅ Schema approved with enhancements

---

### 4. Hexagonal Architecture Compliance

#### Proposed Layer Assignments:

| Component | Proposed Layer | Correct? | Notes |
|-----------|---------------|----------|-------|
| PDF extraction (PyMuPDF) | Infrastructure | ✅ | External dependency adapter |
| Token counting (tiktoken) | Infrastructure | ✅ | External dependency adapter |
| Sentence tokenizing (NLTK) | Infrastructure | ✅ | External dependency adapter |
| Chunking algorithm | Application | ✅ | Business logic orchestration |
| Duplicate detection (hash) | Domain | ✅ | Pure domain logic |
| Rate limiting | Infrastructure | ✅ | External API constraint handling |
| API endpoint | API | ✅ | Thin controller |

**Compliance Score**: 100% ✅

**Port Interfaces Needed** (create in `domain/ports.py`):
```python
from typing import Protocol

class PDFExtractorPort(Protocol):
    async def extract_text(self, file_bytes: bytes) -> str: ...

class TokenCounterPort(Protocol):
    def count_tokens(self, text: str) -> int: ...

class SentenceTokenizerPort(Protocol):
    def tokenize(self, text: str) -> list[str]: ...

class ChunkerPort(Protocol):
    def create_chunks(
        self, 
        text: str, 
        target_min: int = 300,
        target_max: int = 500
    ) -> list[Chunk]: ...
```

**Infrastructure Adapters** (implement in `infrastructure/`):
```
infrastructure/
├── document_processing/
│   ├── pymupdf_extractor.py      # Implements PDFExtractorPort
│   └── __init__.py
├── text_processing/
│   ├── nltk_tokenizer.py         # Implements SentenceTokenizerPort
│   ├── sentence_chunker.py       # Implements ChunkerPort
│   └── __init__.py
└── token_counting/
    ├── tiktoken_counter.py       # Implements TokenCounterPort
    └── __init__.py
```

---

### 5. Constitution Compliance Review

#### Code Quality Standards (Principle I)
- ✅ Clean code: Research demonstrates clear naming, intent-revealing design
- ✅ Maintainability: Functions <50 lines achievable (chunking algo ~40 lines)
- ✅ Documentation: All decisions documented with rationale
- ⚠️ **Action**: Ensure inline code comments explain "why" for complex logic (e.g., normalization regex)

#### Testing Standards (Principle II)
- ✅ Test-first: Research identifies test cases (golden dataset, edge cases)
- ✅ Coverage: Unit tests for chunking, hashing, validation planned
- ✅ Integration tests: PDF → chunks pipeline, rate limiting, rollback tests planned
- ✅ Golden dataset: 10-20 test documents across subjects planned

**No issues found** ✅

#### AI Engineering Standards (Principle III)
- ✅ Provider abstraction: Gemini client already abstracted
- ✅ Streaming: Deferred (acceptable, noted in research)
- ✅ Error handling: Retry logic with exponential backoff specified
- ✅ Token tracking: Logged for every LLM call (per constitution)
- ✅ Quota management: Rate limiter enforces 15 RPM Gemini limit

**No issues found** ✅

#### Architecture & Tech Stack (Principle IV)
- ✅ FastAPI 0.109+ (already in use)
- ✅ Python 3.11+ (already in use)
- ✅ Hexagonal architecture (properly extended)
- ✅ Async-first (all I/O operations async, as shown in research)
- ✅ Type safety: Pydantic models for requests/responses (to be added)

**No issues found** ✅

#### Performance Requirements (Principle V)
- ✅ Ingestion <5s for 3000-word doc (research: ~2s)
- ✅ Embedding <300ms per chunk (Gemini baseline)
- ✅ DB queries indexed (content_hash index planned)
- ✅ Resource usage: +19MB dependencies (acceptable)

**Exceeds requirements** ⭐

#### Zero-Cost Constraints (Principle VI)
- ✅ Gemini free tier only (no paid APIs)
- ✅ Local ChromaDB (no hosted vector DB)
- ✅ Local SQLite (no hosted DB)
- ✅ Rate limiter respects 15 RPM Gemini limit
- ✅ All dependencies local (PyMuPDF, tiktoken, NLTK)

**Perfect compliance** ✅

#### Domain-Agnostic Design (Principle VII)
- ✅ Generic subject tags (biology, programming, history, math)
- ✅ No hardcoded subject-specific logic
- ✅ Subject registry extensible (database-backed)
- ✅ Prompts remain generic (to be verified in API design)

**No issues found** ✅

#### User Experience - API First (Principle VIII)
- ⏳ **Deferred to API design phase**
- Note: Invoke `api-design-principles` skill before generating contracts

---

## Recommendations Summary

### Critical (Must Address Before Phase 1)
1. ✅ **Create port interfaces** in `domain/ports.py` for all external dependencies
2. ✅ **Abstract tiktoken** - DO NOT import in domain layer (infrastructure only)
3. ✅ **Add circuit breaker** to rate limiter (prevent cascading failures)
4. ✅ **Add max queue depth** (100 requests) to prevent memory leaks

### Important (Address During Phase 1)
5. ✅ **Add foreign key constraint** for subject references (data integrity)
6. ✅ **Add ingestion metadata** columns (observability)
7. ✅ **Document NLTK data download** in lifespan handler (startup)

### Nice-to-Have (Consider for v2)
8. 📋 **Persist rate limiter state** to Redis (survive restarts)
9. 📋 **Add soft deletes** to documents table (audit trail)
10. 📋 **Multi-language sentence tokenizers** (Spanish, French)

---

## Decision Log

### ADR-001: Use PyMuPDF for PDF Extraction
**Status**: Accepted  
**Rationale**: 6x faster than alternatives, clean text output, minimal dependencies  
**Trade-offs**: Binary dependency (acceptable), potential macOS ARM compatibility issues (mitigated by fallback plan)

### ADR-002: Use tiktoken for Token Counting
**Status**: Accepted with Caveat  
**Rationale**: Fast, accurate, industry standard  
**Caveat**: MUST be abstracted via port interface, not imported in domain  
**Trade-offs**: <5% mismatch with Gemini tokenizer (acceptable)

### ADR-003: Use NLTK Punkt for Sentence Tokenization
**Status**: Accepted  
**Rationale**: 98%+ accuracy, lightweight (3MB), fast  
**Trade-offs**: English-only for v1 (acceptable), requires data download at startup

### ADR-004: In-Memory Rate Limiter
**Status**: Accepted for v1  
**Rationale**: Simple, zero-cost, sufficient for single-instance deployment  
**Trade-offs**: Lost on restart (acceptable), not suitable for multi-instance (deferred to v2)

### ADR-005: Sentence-Priority Chunking
**Status**: Accepted  
**Rationale**: Directly implements clarified requirement, preserves semantic integrity  
**Trade-offs**: Chunks may exceed 500 tokens (intentional per clarification Q2)

---

## Phase 1 Readiness Checklist

- [x] All technology choices vetted and approved
- [x] Hexagonal architecture alignment verified
- [x] Constitution compliance confirmed (100%)
- [x] Port interfaces specified
- [x] Infrastructure adapter structure defined
- [x] Database schema reviewed and enhanced
- [x] Critical recommendations documented
- [ ] **Next**: Generate data-model.md with port interfaces
- [ ] **Next**: Invoke api-design-principles skill
- [ ] **Next**: Generate API contracts (OpenAPI)

---

## Approval

**Status**: ✅ **APPROVED FOR PHASE 1**

**Senior Architect Sign-off**: The proposed design is architecturally sound, aligns with constitutional principles, and is ready for detailed design (data model, API contracts). Address the 4 critical recommendations before finalizing Phase 1 artifacts.

**Estimated Implementation Complexity**: ⭐⭐⭐ (Moderate)
- Well-researched, clear requirements, existing patterns to follow
- Main complexity: Integrating 3 new libraries (PyMuPDF, tiktoken, NLTK)
- Risk: Low (all dependencies vetted, fallbacks identified)

**Confidence Level**: 95%

---

**END OF ARCHITECTURE REVIEW**
