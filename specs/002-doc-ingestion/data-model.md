# Data Model: Document Ingestion and Knowledge Base Management

**Feature**: Document Ingestion  
**Branch**: `002-document-ingestion`  
**Phase**: Phase 1 Design  
**Status**: Complete

---

## Overview

This document defines the data model for document ingestion, including domain entities, database schema, port interfaces (hexagonal architecture), and entity relationships.

**Architecture Pattern**: Hexagonal (Ports & Adapters)  
**Persistence**: SQLite (local, async via aiosqlite)  
**Vector Store**: ChromaDB (local, persistent)

---

## Domain Model

### Core Entities

#### 1. Document

Represents an uploaded educational document.

**Domain Class** (`src/courseflow/domain/models.py`):
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib
import re

@dataclass
class Document:
    """Domain entity representing an ingested document."""
    
    id: str
    filename: str
    subject: str  # References Subject.name
    content_hash: str  # SHA-256 hex digest
    file_format: str  # "markdown", "txt", "pdf"
    file_size_bytes: int
    chunks_created: int
    ingestion_time_ms: int
    created_at: datetime
    
    @staticmethod
    def compute_content_hash(content: str) -> str:
        """
        Compute SHA-256 hash of normalized content.
        
        Normalization rules (per Clarification Q1):
        - Strip leading/trailing whitespace
        - Normalize line endings (CRLF → LF)
        - Collapse multiple spaces to single space
        - Collapse multiple newlines to single newline
        """
        # Normalize content
        text = content.strip()
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        
        # Compute SHA-256 hash
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, existing_hash: str) -> bool:
        """Check if this document is a duplicate based on content hash."""
        return self.content_hash == existing_hash
```

**Attributes**:
- `id` (str): Unique identifier (UUID or similar)
- `filename` (str): Original filename (e.g., "photosynthesis.pdf")
- `subject` (str): Subject tag (foreign key to subjects.name)
- `content_hash` (str): SHA-256 hash of normalized content (64-char hex)
- `file_format` (str): File type ("markdown", "txt", "pdf")
- `file_size_bytes` (int): Original file size in bytes
- `chunks_created` (int): Number of chunks created from this document
- `ingestion_time_ms` (int): Total processing time in milliseconds
- `created_at` (datetime): Ingestion timestamp (ISO 8601)

**Invariants**:
- `content_hash` must be globally unique (prevents duplicates)
- `subject` must exist in subjects table
- `chunks_created` must match actual chunk count in database
- `file_format` must be one of: "markdown", "txt", "pdf"

---

#### 2. Chunk

Represents a semantic segment of a document optimized for retrieval.

**Domain Class** (`src/courseflow/domain/models.py`):
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Chunk:
    """Domain entity representing a document chunk."""
    
    id: str
    document_id: str  # References Document.id
    chunk_index: int  # Sequential position (0-based)
    text: str  # Chunk content (300-500 tokens typical)
    token_count: int  # Actual token count
    
    # Metadata inherited from parent document
    source_filename: str
    subject: str
    
    # Vector embedding (stored in ChromaDB, not SQLite)
    embedding: Optional[list[float]] = None
    
    def __post_init__(self):
        """Validate chunk invariants."""
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")
        if not self.text.strip():
            raise ValueError("chunk text cannot be empty")
        if self.token_count <= 0:
            raise ValueError("token_count must be positive")
```

**Attributes**:
- `id` (str): Unique identifier
- `document_id` (str): Parent document reference (foreign key)
- `chunk_index` (int): Position in original document (0, 1, 2, ...)
- `text` (str): Chunk content (complete sentences, 300-500 tokens target)
- `token_count` (int): Actual token count (may exceed 500 for long sentences)
- `source_filename` (str): Denormalized for query performance
- `subject` (str): Denormalized for filtering
- `embedding` (list[float]): 768-dim vector (stored in ChromaDB, not SQLite)

**Invariants**:
- Chunk text MUST preserve sentence integrity (no mid-sentence splits)
- `chunk_index` MUST be sequential within a document (0, 1, 2, ...)
- `token_count` typically 300-500, but can exceed for sentence integrity
- No duplicate chunk_index within same document_id

---

#### 3. Subject

Represents a subject area/category for documents.

**Domain Class** (`src/courseflow/domain/models.py`):
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Subject:
    """Domain entity representing a subject category."""
    
    id: str
    name: str  # Lowercase slug (e.g., "biology", "programming")
    display_name: str  # Human-readable (e.g., "Biology", "Programming")
    created_at: datetime
    
    def __post_init__(self):
        """Validate subject invariants."""
        if not self.name.islower():
            raise ValueError("name must be lowercase")
        if len(self.name) > 50:
            raise ValueError("name must be ≤50 characters")
        if not self.name.replace('-', '').replace('_', '').isalnum():
            raise ValueError("name must be alphanumeric (with - or _)")
```

**Attributes**:
- `id` (str): Unique identifier
- `name` (str): Lowercase slug for API/DB (e.g., "biology", "world-history")
- `display_name` (str): Human-readable name for UI (e.g., "Biology", "World History")
- `created_at` (datetime): When subject was added

**Invariants**:
- `name` must be unique (enforced by DB UNIQUE constraint)
- `name` must be lowercase, alphanumeric (with hyphens/underscores)
- `name` length ≤50 characters (per Assumption #10)

**Predefined Subjects** (v1):
- `biology` → "Biology"
- `programming` → "Programming"
- `history` → "History"
- `mathematics` → "Mathematics"
- `general` → "General"

---

#### 4. IngestionResult

Represents the outcome of a document upload operation (transient, not persisted).

**Domain Class** (`src/courseflow/domain/models.py`):
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class IngestionResult:
    """Result of document ingestion operation."""
    
    document_id: str
    filename: str
    success: bool
    chunks_created: int
    ingestion_time_ms: int
    skipped: bool  # True if duplicate detected
    error_message: Optional[str] = None
    
    def to_api_response(self) -> dict:
        """Convert to API response format."""
        if self.error_message:
            return {
                "success": False,
                "error": self.error_message,
                "document_id": None,
            }
        
        return {
            "success": True,
            "data": {
                "document_id": self.document_id,
                "filename": self.filename,
                "chunks_created": self.chunks_created,
                "ingestion_time_ms": self.ingestion_time_ms,
                "skipped": self.skipped,
            },
            "error": None,
        }
```

**Attributes**:
- `document_id` (str): ID of ingested document (or None if failed)
- `filename` (str): Original filename
- `success` (bool): True if ingestion succeeded
- `chunks_created` (int): Number of chunks created (0 if skipped/failed)
- `ingestion_time_ms` (int): Total processing time
- `skipped` (bool): True if duplicate detected (success=True, chunks=0)
- `error_message` (str | None): Error details if failed

---

## Port Interfaces (Hexagonal Architecture)

Defined in `src/courseflow/domain/ports.py`:

```python
"""
Port interfaces for hexagonal architecture.
Domain layer defines contracts; infrastructure layer implements adapters.
"""

from typing import Protocol, runtime_checkable
from courseflow.domain.models import Chunk

@runtime_checkable
class PDFExtractorPort(Protocol):
    """Port for PDF text extraction."""
    
    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Extract plain text from PDF file.
        
        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename (for error messages)
        
        Returns:
            Plain text content
        
        Raises:
            PDFCorruptedError: If PDF is corrupted or password-protected
            InvalidFormatError: If file is not a valid PDF
        """
        ...


@runtime_checkable
class TokenCounterPort(Protocol):
    """Port for token counting."""
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using LLM tokenizer.
        
        Args:
            text: Text to tokenize
        
        Returns:
            Token count (integer)
        """
        ...


@runtime_checkable
class SentenceTokenizerPort(Protocol):
    """Port for sentence boundary detection."""
    
    def tokenize_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.
        
        Args:
            text: Document text
        
        Returns:
            List of sentences (preserving original whitespace)
        """
        ...


@runtime_checkable
class ChunkerPort(Protocol):
    """Port for semantic text chunking."""
    
    def create_chunks(
        self,
        text: str,
        target_min_tokens: int = 300,
        target_max_tokens: int = 500,
    ) -> list[Chunk]:
        """
        Split text into semantic chunks.
        
        Args:
            text: Document text
            target_min_tokens: Minimum tokens per chunk (soft limit)
            target_max_tokens: Maximum tokens per chunk (soft limit, can exceed for sentences)
        
        Returns:
            List of Chunk objects (without embeddings or IDs)
        
        Invariants:
            - Every chunk preserves sentence integrity (no mid-sentence splits)
            - Chunks are sequential (index 0, 1, 2, ...)
            - No orphan sentences (every sentence belongs to a chunk)
        """
        ...


@runtime_checkable
class DocumentRepositoryPort(Protocol):
    """Port for document persistence."""
    
    async def save_document(self, document: Document) -> None:
        """Save document to database."""
        ...
    
    async def find_by_content_hash(self, content_hash: str) -> Document | None:
        """Find document by content hash (duplicate detection)."""
        ...
    
    async def find_by_id(self, document_id: str) -> Document | None:
        """Find document by ID."""
        ...


@runtime_checkable
class ChunkRepositoryPort(Protocol):
    """Port for chunk persistence."""
    
    async def save_chunks(self, chunks: list[Chunk]) -> None:
        """Batch save chunks to database and vector store."""
        ...
    
    async def delete_chunks_by_document_id(self, document_id: str) -> None:
        """Delete all chunks for a document (rollback support)."""
        ...
    
    async def find_chunks_by_document_id(self, document_id: str) -> list[Chunk]:
        """Retrieve all chunks for a document."""
        ...


@runtime_checkable
class SubjectRepositoryPort(Protocol):
    """Port for subject management."""
    
    async def find_all(self) -> list[Subject]:
        """Get all available subjects."""
        ...
    
    async def find_by_name(self, name: str) -> Subject | None:
        """Find subject by name slug."""
        ...
    
    async def subject_exists(self, name: str) -> bool:
        """Check if subject exists (for validation)."""
        ...
```

---

## Database Schema (SQLite)

### Tables

#### documents

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,                    -- UUID v4
    filename TEXT NOT NULL,                 -- Original filename
    subject TEXT NOT NULL,                  -- Foreign key to subjects.name
    content_hash TEXT UNIQUE NOT NULL,      -- SHA-256 hex (64 chars)
    file_format TEXT NOT NULL,              -- "markdown" | "txt" | "pdf"
    file_size_bytes INTEGER NOT NULL,       -- Original file size
    chunks_created INTEGER NOT NULL,        -- Number of chunks
    ingestion_time_ms INTEGER NOT NULL,     -- Processing time
    created_at TEXT NOT NULL,               -- ISO 8601 timestamp
    
    FOREIGN KEY (subject) REFERENCES subjects(name) ON DELETE RESTRICT
);

-- Indexes
CREATE UNIQUE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_subject ON documents(subject);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
```

**Rationale**:
- `content_hash` UNIQUE prevents duplicates (idempotent ingestion)
- Foreign key to subjects enforces referential integrity
- Indexes on content_hash (duplicate detection), subject (filtering), created_at (chronological queries)

---

#### chunks

```sql
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,                    -- UUID v4
    document_id TEXT NOT NULL,              -- Foreign key to documents.id
    chunk_index INTEGER NOT NULL,           -- Sequential position (0-based)
    text TEXT NOT NULL,                     -- Chunk content
    token_count INTEGER NOT NULL,           -- Actual token count
    source_filename TEXT NOT NULL,          -- Denormalized from document
    subject TEXT NOT NULL,                  -- Denormalized from document
    
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE (document_id, chunk_index)       -- No duplicate indexes per document
);

-- Indexes
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_subject ON chunks(subject);
```

**Rationale**:
- `chunk_index` within document ensures ordering
- Denormalized `source_filename` and `subject` for query performance (avoid JOINs in retrieval)
- CASCADE delete ensures chunks are removed when document is deleted (future feature)
- UNIQUE constraint on (document_id, chunk_index) prevents duplicates

**Note**: Chunk embeddings are stored in ChromaDB (vector store), not SQLite

---

#### subjects

```sql
CREATE TABLE subjects (
    id TEXT PRIMARY KEY,                    -- UUID v4 or slug-based ID
    name TEXT UNIQUE NOT NULL,              -- Lowercase slug (e.g., "biology")
    display_name TEXT NOT NULL,             -- Human-readable (e.g., "Biology")
    created_at TEXT NOT NULL                -- ISO 8601 timestamp
);

CREATE UNIQUE INDEX idx_subjects_name ON subjects(name);

-- Pre-populate subjects for v1
INSERT INTO subjects (id, name, display_name, created_at) VALUES
    ('subj_bio', 'biology', 'Biology', datetime('now')),
    ('subj_prog', 'programming', 'Programming', datetime('now')),
    ('subj_hist', 'history', 'History', datetime('now')),
    ('subj_math', 'mathematics', 'Mathematics', datetime('now')),
    ('subj_gen', 'general', 'General', datetime('now'));
```

**Rationale**:
- Predefined list prevents "bio" vs "biology" inconsistencies
- Extensible (admin can add subjects in v2)
- UNIQUE index on `name` enforces consistency

---

### Entity Relationships

```
┌─────────────────┐
│    subjects     │
│─────────────────│
│ id (PK)         │
│ name (UNIQUE)   │◄──────────┐
│ display_name    │           │
│ created_at      │           │ FK
└─────────────────┘           │
                              │
                   ┌──────────┴──────────┐
                   │     documents        │
                   │──────────────────────│
                   │ id (PK)              │
                   │ filename             │
                   │ subject (FK)         │
                   │ content_hash (UNIQUE)│
                   │ file_format          │
                   │ file_size_bytes      │
                   │ chunks_created       │
                   │ ingestion_time_ms    │
                   │ created_at           │
                   └──────────┬───────────┘
                              │
                              │ 1:N (CASCADE DELETE)
                              │
                   ┌──────────▼───────────┐
                   │      chunks          │
                   │──────────────────────│
                   │ id (PK)              │
                   │ document_id (FK)     │
                   │ chunk_index          │
                   │ text                 │
                   │ token_count          │
                   │ source_filename      │
                   │ subject              │
                   └──────────────────────┘
                              │
                              │ 1:1 (embedding)
                              │
                   ┌──────────▼───────────┐
                   │   ChromaDB           │
                   │──────────────────────│
                   │ chunk_id (metadata)  │
                   │ embedding (768-dim)  │
                   │ document_id (filter) │
                   │ subject (filter)     │
                   └──────────────────────┘
```

**Relationships**:
1. **Subject → Document** (1:N): One subject has many documents
2. **Document → Chunk** (1:N): One document has many chunks (CASCADE DELETE)
3. **Chunk → Embedding** (1:1): One chunk has one embedding (in ChromaDB)

---

## ChromaDB Schema

**Collection Name**: `document_chunks`

**Metadata Fields**:
```python
{
    "chunk_id": str,           # Matches chunks.id in SQLite
    "document_id": str,        # For filtering by document
    "subject": str,            # For filtering by subject
    "source_filename": str,    # For result display
    "chunk_index": int,        # For ordering
}
```

**Embedding Dimension**: 768 (Gemini text-embedding-004)

**Distance Metric**: Cosine similarity

**Usage**:
```python
# Insert chunks
collection.add(
    ids=[chunk.id for chunk in chunks],
    embeddings=[chunk.embedding for chunk in chunks],
    metadatas=[{
        "chunk_id": chunk.id,
        "document_id": chunk.document_id,
        "subject": chunk.subject,
        "source_filename": chunk.source_filename,
        "chunk_index": chunk.chunk_index,
    } for chunk in chunks],
    documents=[chunk.text for chunk in chunks],
)

# Query with subject filter
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"subject": "biology"},  # Optional filter
)
```

---

## Data Flow Diagram

```
┌──────────────┐
│ User uploads │
│ PDF file     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ API Layer: POST /api/v1/ingest                       │
│  - Validate file format, size                        │
│  - Generate request_id for tracing                   │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ Application Layer: IngestionService                  │
│  1. Extract text (PDFExtractorPort)                  │
│  2. Compute content hash (Document.compute_hash)     │
│  3. Check duplicate (DocumentRepositoryPort)         │
│     ├─ If duplicate: Return IngestionResult(skipped) │
│     └─ If new: Continue                              │
│  4. Validate subject (SubjectRepositoryPort)         │
│  5. Create chunks (ChunkerPort)                      │
│  6. Generate embeddings (EmbeddingPort)              │
│  7. Save document + chunks (atomic transaction)      │
│  8. Return IngestionResult                           │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ Infrastructure Layer: Repositories                   │
│  - SQLite: Save document metadata, chunks            │
│  - ChromaDB: Save embeddings                         │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Persistent   │
│ Storage      │
└──────────────┘
```

---

## Validation Rules

### Document Validation

```python
# API Layer: src/courseflow/api/routes/ingest.py
from pydantic import BaseModel, Field, field_validator

class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    
    filename: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., pattern=r'^[a-z][a-z0-9\-_]*$', max_length=50)
    
    @field_validator('filename')
    @classmethod
    def validate_file_extension(cls, v: str) -> str:
        allowed_extensions = {'.md', '.txt', '.pdf'}
        ext = v.lower().split('.')[-1]
        if f'.{ext}' not in allowed_extensions:
            raise ValueError(f'Invalid file format. Allowed: {allowed_extensions}')
        return v
```

### File Size Validation

- **Maximum**: 10 MB (10,485,760 bytes) per Assumption #9
- **Minimum**: 1 byte (reject empty files)

### Content Validation

- **Empty content**: Reject if text.strip() is empty after extraction
- **Whitespace-only**: Reject if content is only whitespace/newlines

### Subject Validation

- **Existence check**: Subject must exist in `subjects` table
- **Format**: Lowercase, alphanumeric with hyphens/underscores only

---

## Migration Strategy

### From v0 (No Ingestion) → v1 (Ingestion)

**New Tables**:
```sql
-- Run migration script
CREATE TABLE subjects (...);
CREATE TABLE documents (...);
CREATE TABLE chunks (...);

-- Populate subjects
INSERT INTO subjects VALUES (...);
```

**Existing Data**: No changes to existing ChromaDB collection (backward compatible)

**Rollback**: Drop new tables if migration fails

### Future v2 Enhancements

**Soft Deletes**:
```sql
ALTER TABLE documents ADD COLUMN deleted_at TEXT NULL;
```

**Document Versioning**:
```sql
CREATE TABLE document_versions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

---

## Testing Strategy

### Unit Tests (`tests/unit/domain/`)

```python
def test_compute_content_hash_normalization():
    """Verify hash ignores formatting differences."""
    content1 = "Hello  World\r\n\r\nTest"
    content2 = "Hello World\n\nTest"
    
    hash1 = Document.compute_content_hash(content1)
    hash2 = Document.compute_content_hash(content2)
    
    assert hash1 == hash2  # Same normalized content

def test_chunk_index_sequential():
    """Verify chunks maintain sequential order."""
    chunks = [
        Chunk(id="1", document_id="doc1", chunk_index=0, text="First", token_count=10),
        Chunk(id="2", document_id="doc1", chunk_index=1, text="Second", token_count=10),
    ]
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1

def test_subject_name_validation():
    """Verify subject name must be lowercase."""
    with pytest.raises(ValueError, match="lowercase"):
        Subject(id="1", name="Biology", display_name="Biology", created_at=datetime.now())
```

### Integration Tests (`tests/integration/`)

```python
@pytest.mark.asyncio
async def test_duplicate_detection():
    """Verify duplicate documents are skipped."""
    repo = DocumentRepository(db_path)
    
    doc1 = Document(id="1", content_hash="abc123", ...)
    await repo.save_document(doc1)
    
    # Attempt duplicate
    duplicate = await repo.find_by_content_hash("abc123")
    assert duplicate is not None
    assert duplicate.id == doc1.id

@pytest.mark.asyncio
async def test_cascade_delete_chunks():
    """Verify chunks are deleted when document is deleted."""
    # Save document + chunks
    await doc_repo.save_document(doc)
    await chunk_repo.save_chunks(chunks)
    
    # Delete document
    await doc_repo.delete(doc.id)
    
    # Verify chunks are gone
    remaining = await chunk_repo.find_by_document_id(doc.id)
    assert len(remaining) == 0
```

### Contract Tests

```python
def test_pdf_extractor_port_contract():
    """Verify adapter implements PDFExtractorPort."""
    from courseflow.infrastructure.document_processing import PyMuPDFExtractor
    
    extractor = PyMuPDFExtractor()
    assert isinstance(extractor, PDFExtractorPort)
```

---

## Summary

**Entities**: 3 (Document, Chunk, Subject) + 1 transient (IngestionResult)  
**Database Tables**: 3 (documents, chunks, subjects)  
**Port Interfaces**: 6 (PDF, Token, Sentence, Chunker, DocumentRepo, ChunkRepo, SubjectRepo)  
**Adapters**: 7 (PyMuPDF, tiktoken, NLTK, SQLite repos, ChromaDB)

**Design Principles Applied**:
- ✅ Hexagonal architecture (domain isolated from infrastructure)
- ✅ Domain-driven design (rich domain models with behavior)
- ✅ Single Responsibility (each entity has one purpose)
- ✅ Interface segregation (fine-grained port interfaces)
- ✅ Dependency inversion (application depends on ports, not implementations)

**Constitution Compliance**: 100% ✅

**Next Steps**: 
1. Invoke `api-design-principles` skill
2. Generate OpenAPI contracts (`contracts/ingest-api.yaml`)
3. Generate quickstart.md

---

**END OF DATA MODEL**
