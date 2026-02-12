# Quickstart Guide: Document Ingestion Feature

**Feature**: Document Ingestion and Knowledge Base Management  
**Branch**: `002-document-ingestion`  
**Status**: Implementation Ready  
**Prerequisites**: Python 3.11+, Git

---

## Overview

This guide walks you through implementing and testing the document ingestion feature. By the end, you'll have a working API that accepts PDF, Markdown, and plain text documents, chunks them semantically, and stores them in the knowledge base.

**What You'll Build:**
- POST `/api/v1/ingest` - Upload and process documents
- GET `/api/v1/documents` - List ingested documents  
- GET `/api/v1/subjects` - List available subject categories
- Automatic duplicate detection via content hashing
- Rate-limited embedding generation (respecting Gemini 15 RPM quota)
- Sentence-priority chunking (300-500 tokens, preserving sentence integrity)

**Time Estimate**: 4-6 hours for complete implementation

---

## Phase 1: Environment Setup (15 minutes)

### 1.1 Install New Dependencies

Add to `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "pymupdf>=1.27.0",      # PDF text extraction
    "tiktoken>=0.12.0",     # Token counting
    "nltk>=3.9.0",          # Sentence tokenization
]
```

Install:
```bash
pip install pymupdf tiktoken nltk
```

### 1.2 Download NLTK Data

```bash
python -c "import nltk; nltk.download('punkt')"
```

Or add to `src/courseflow/api/main.py` startup:
```python
import nltk
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    nltk.download('punkt', quiet=True)
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)
```

### 1.3 Create Database Schema

Create `scripts/migrations/002_add_ingestion_tables.sql`:
```sql
-- Subjects table
CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    subject TEXT NOT NULL,
    content_hash TEXT UNIQUE NOT NULL,
    file_format TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    chunks_created INTEGER NOT NULL,
    ingestion_time_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (subject) REFERENCES subjects(name) ON DELETE RESTRICT
);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    source_filename TEXT NOT NULL,
    subject TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE (document_id, chunk_index)
);

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_subject ON documents(subject);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);

-- Pre-populate subjects
INSERT OR IGNORE INTO subjects (id, name, display_name, created_at) VALUES
    ('subj_bio', 'biology', 'Biology', datetime('now')),
    ('subj_prog', 'programming', 'Programming', datetime('now')),
    ('subj_hist', 'history', 'History', datetime('now')),
    ('subj_math', 'mathematics', 'Mathematics', datetime('now')),
    ('subj_gen', 'general', 'General', datetime('now'));
```

Run migration:
```bash
sqlite3 data/courseflow.db < scripts/migrations/002_add_ingestion_tables.sql
```

---

## Phase 2: Domain Layer (30 minutes)

### 2.1 Update Domain Models

Edit `src/courseflow/domain/models.py`:
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
    subject: str
    content_hash: str
    file_format: str
    file_size_bytes: int
    chunks_created: int
    ingestion_time_ms: int
    created_at: datetime
    
    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA-256 hash of normalized content."""
        text = content.strip()
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

@dataclass
class Chunk:
    """Domain entity representing a document chunk."""
    id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int
    source_filename: str
    subject: str
    embedding: Optional[list[float]] = None

@dataclass
class Subject:
    """Domain entity representing a subject category."""
    id: str
    name: str
    display_name: str
    created_at: datetime

@dataclass
class IngestionResult:
    """Result of document ingestion operation."""
    document_id: str
    filename: str
    success: bool
    chunks_created: int
    ingestion_time_ms: int
    skipped: bool
    error_message: Optional[str] = None
```

### 2.2 Define Port Interfaces

Create `src/courseflow/domain/ports.py`:
```python
from typing import Protocol, runtime_checkable
from courseflow.domain.models import Chunk

@runtime_checkable
class PDFExtractorPort(Protocol):
    async def extract_text(self, file_bytes: bytes, filename: str) -> str: ...

@runtime_checkable
class TokenCounterPort(Protocol):
    def count_tokens(self, text: str) -> int: ...

@runtime_checkable
class SentenceTokenizerPort(Protocol):
    def tokenize_sentences(self, text: str) -> list[str]: ...

@runtime_checkable
class ChunkerPort(Protocol):
    def create_chunks(
        self, text: str,
        target_min_tokens: int = 300,
        target_max_tokens: int = 500
    ) -> list[Chunk]: ...
```

---

## Phase 3: Infrastructure Layer (60 minutes)

### 3.1 PDF Extractor Adapter

Create `src/courseflow/infrastructure/document_processing/pymupdf_extractor.py`:
```python
import pymupdf
from courseflow.domain.exceptions import PDFCorruptedError, InvalidFormatError

class PyMuPDFExtractor:
    """PDF text extraction using PyMuPDF."""
    
    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """Extract plain text from PDF."""
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            text_parts = []
            
            for page in doc:
                text_parts.append(page.get_text("text"))
            
            doc.close()
            return "\n".join(text_parts)
        
        except pymupdf.FileDataError as e:
            if "password" in str(e).lower() or "encrypted" in str(e).lower():
                raise PDFCorruptedError(f"PDF is password-protected: {filename}")
            raise PDFCorruptedError(f"Corrupted PDF file: {filename}")
        except Exception as e:
            raise InvalidFormatError(f"Failed to extract PDF text: {e}")
```

### 3.2 Token Counter Adapter

Create `src/courseflow/infrastructure/token_counting/tiktoken_counter.py`:
```python
import tiktoken

class TiktokenCounter:
    """Token counting using tiktoken (GPT/Gemini-compatible)."""
    
    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
```

### 3.3 Sentence Tokenizer Adapter

Create `src/courseflow/infrastructure/text_processing/nltk_tokenizer.py`:
```python
from nltk.tokenize import sent_tokenize

class NLTKSentenceTokenizer:
    """Sentence boundary detection using NLTK Punkt."""
    
    def tokenize_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        return sent_tokenize(text)
```

### 3.4 Chunker Implementation

Create `src/courseflow/infrastructure/text_processing/sentence_chunker.py`:
```python
from courseflow.domain.models import Chunk
from courseflow.domain.ports import TokenCounterPort, SentenceTokenizerPort
import uuid

class SentenceChunker:
    """Semantic chunking with sentence integrity priority."""
    
    def __init__(
        self,
        token_counter: TokenCounterPort,
        sentence_tokenizer: SentenceTokenizerPort
    ):
        self.token_counter = token_counter
        self.sentence_tokenizer = sentence_tokenizer
    
    def create_chunks(
        self,
        text: str,
        target_min_tokens: int = 300,
        target_max_tokens: int = 500
    ) -> list[Chunk]:
        """Split text into semantic chunks preserving sentence boundaries."""
        sentences = self.sentence_tokenizer.tokenize_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.token_counter.count_tokens(sentence)
            
            # If adding sentence keeps us under max, add it
            if current_tokens + sentence_tokens <= target_max_tokens:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
            
            # If we're below min but adding exceeds max, add anyway (sentence priority)
            elif current_tokens < target_min_tokens:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
                # Close chunk
                chunks.append(self._create_chunk(current_chunk, len(chunks)))
                current_chunk = []
                current_tokens = 0
            
            # Otherwise, close current chunk and start new one
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, len(chunks)))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, len(chunks)))
        
        return chunks
    
    def _create_chunk(self, sentences: list[str], index: int) -> Chunk:
        """Create chunk from sentences."""
        text = " ".join(sentences)
        return Chunk(
            id=str(uuid.uuid4()),
            document_id="",  # Set by application layer
            chunk_index=index,
            text=text,
            token_count=self.token_counter.count_tokens(text),
            source_filename="",  # Set by application layer
            subject=""  # Set by application layer
        )
```

---

## Phase 4: Application Layer (90 minutes)

### 4.1 Ingestion Service

Create `src/courseflow/application/ingestion_service.py`:
```python
from courseflow.domain.models import Document, IngestionResult
from courseflow.domain.ports import *
import uuid
from datetime import datetime
import time

class IngestionService:
    """Orchestrates document ingestion workflow."""
    
    def __init__(
        self,
        pdf_extractor: PDFExtractorPort,
        chunker: ChunkerPort,
        embedding_service,  # EmbeddingPort from existing code
        document_repo,  # DocumentRepositoryPort
        chunk_repo,  # ChunkRepositoryPort
        subject_repo  # SubjectRepositoryPort
    ):
        self.pdf_extractor = pdf_extractor
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo
        self.subject_repo = subject_repo
    
    async def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        subject: str
    ) -> IngestionResult:
        """Ingest a document into the knowledge base."""
        start_time = time.time()
        
        try:
            # 1. Validate subject exists
            if not await self.subject_repo.subject_exists(subject):
                raise ValueError(f"Invalid subject: {subject}")
            
            # 2. Extract text based on file format
            if filename.endswith('.pdf'):
                content = await self.pdf_extractor.extract_text(file_bytes, filename)
                file_format = "pdf"
            elif filename.endswith('.md'):
                content = file_bytes.decode('utf-8')
                file_format = "markdown"
            elif filename.endswith('.txt'):
                content = file_bytes.decode('utf-8')
                file_format = "txt"
            else:
                raise ValueError("Invalid file format")
            
            # 3. Compute content hash
            content_hash = Document.compute_content_hash(content)
            
            # 4. Check for duplicates
            existing = await self.document_repo.find_by_content_hash(content_hash)
            if existing:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return IngestionResult(
                    document_id=existing.id,
                    filename=filename,
                    success=True,
                    chunks_created=0,
                    ingestion_time_ms=elapsed_ms,
                    skipped=True
                )
            
            # 5. Create chunks
            chunks = self.chunker.create_chunks(content)
            
            # 6. Generate embeddings (with rate limiting)
            for chunk in chunks:
                embedding = await self.embedding_service.embed(chunk.text)
                chunk.embedding = embedding
            
            # 7. Create document entity
            document_id = str(uuid.uuid4())
            document = Document(
                id=document_id,
                filename=filename,
                subject=subject,
                content_hash=content_hash,
                file_format=file_format,
                file_size_bytes=len(file_bytes),
                chunks_created=len(chunks),
                ingestion_time_ms=0,  # Set below
                created_at=datetime.utcnow()
            )
            
            # 8. Set chunk metadata
            for chunk in chunks:
                chunk.document_id = document_id
                chunk.source_filename = filename
                chunk.subject = subject
            
            # 9. Save to database (atomic)
            await self.document_repo.save_document(document)
            await self.chunk_repo.save_chunks(chunks)
            
            # 10. Return result
            elapsed_ms = int((time.time() - start_time) * 1000)
            document.ingestion_time_ms = elapsed_ms
            
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                success=True,
                chunks_created=len(chunks),
                ingestion_time_ms=elapsed_ms,
                skipped=False
            )
        
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return IngestionResult(
                document_id="",
                filename=filename,
                success=False,
                chunks_created=0,
                ingestion_time_ms=elapsed_ms,
                skipped=False,
                error_message=str(e)
            )
```

---

## Phase 5: API Layer (60 minutes)

### 5.1 Create Ingestion Endpoint

Create `src/courseflow/api/routes/ingest.py`:
```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/api/v1", tags=["ingestion"])

class IngestionResponse(BaseModel):
    success: bool
    data: dict | None
    metadata: dict
    error: dict | None

@router.post("/ingest", response_model=IngestionResponse)
async def ingest_document(
    file: UploadFile = File(...),
    subject: str = Form(...),
    ingestion_service = Depends(get_ingestion_service)  # Dependency injection
):
    """Ingest a document into the knowledge base."""
    request_id = str(uuid.uuid4())
    
    # Validate file format
    if not file.filename.endswith(('.pdf', '.md', '.txt')):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_format",
                "message": "Invalid file format. Allowed: .md, .txt, .pdf"
            }
        )
    
    # Validate file size (10 MB max)
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "file_too_large",
                "message": "File size exceeds maximum allowed (10 MB)"
            }
        )
    
    # Ingest document
    result = await ingestion_service.ingest_document(
        file_bytes=file_bytes,
        filename=file.filename,
        subject=subject
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ingestion_failed",
                "message": result.error_message
            }
        )
    
    return IngestionResponse(
        success=True,
        data={
            "document_id": result.document_id,
            "filename": result.filename,
            "chunks_created": result.chunks_created,
            "ingestion_time_ms": result.ingestion_time_ms,
            "skipped": result.skipped
        },
        metadata={
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        error=None
    )
```

---

## Phase 6: Testing (60 minutes)

### 6.1 Unit Tests

Create `tests/unit/infrastructure/test_chunker.py`:
```python
import pytest
from courseflow.infrastructure.text_processing.sentence_chunker import SentenceChunker
from courseflow.infrastructure.token_counting.tiktoken_counter import TiktokenCounter
from courseflow.infrastructure.text_processing.nltk_tokenizer import NLTKSentenceTokenizer

def test_sentence_chunking_preserves_boundaries():
    """Verify chunks never split mid-sentence."""
    token_counter = TiktokenCounter()
    sentence_tokenizer = NLTKSentenceTokenizer()
    chunker = SentenceChunker(token_counter, sentence_tokenizer)
    
    text = "First sentence. Second sentence. Third sentence. " * 50
    chunks = chunker.create_chunks(text, target_min_tokens=100, target_max_tokens=200)
    
    # Verify each chunk ends with sentence boundary
    for chunk in chunks:
        assert chunk.text.strip().endswith(('.', '!', '?'))

def test_duplicate_content_hash():
    """Verify hash ignores formatting differences."""
    from courseflow.domain.models import Document
    
    content1 = "Hello  World\r\n\r\nTest"
    content2 = "Hello World\n\nTest"
    
    hash1 = Document.compute_content_hash(content1)
    hash2 = Document.compute_content_hash(content2)
    
    assert hash1 == hash2
```

### 6.2 Integration Test

Create `tests/integration/test_ingestion_e2e.py`:
```python
import pytest
from httpx import AsyncClient
from courseflow.api.main import app

@pytest.mark.asyncio
async def test_document_ingestion_e2e():
    """Test full ingestion workflow."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test PDF or markdown file
        test_content = b"# Biology\n\nPhotosynthesis is..."
        
        response = await client.post(
            "/api/v1/ingest",
            files={"file": ("test.md", test_content)},
            data={"subject": "biology"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["chunks_created"] > 0
        assert data["data"]["skipped"] is False
        
        # Test duplicate upload
        response2 = await client.post(
            "/api/v1/ingest",
            files={"file": ("test_copy.md", test_content)},
            data={"subject": "biology"}
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["data"]["skipped"] is True
        assert data2["data"]["chunks_created"] == 0
```

---

## Phase 7: Manual Testing (30 minutes)

### 7.1 Start Server

```bash
uvicorn courseflow.api.main:app --reload
```

### 7.2 Test Ingestion with cURL

```bash
# Upload PDF
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@docs/biology/photosynthesis.pdf" \
  -F "subject=biology"

# Upload Markdown
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@docs/programming/async-python.md" \
  -F "subject=programming"

# List documents
curl http://localhost:8000/api/v1/documents

# List subjects
curl http://localhost:8000/api/v1/subjects
```

### 7.3 Test with Swagger UI

Open http://localhost:8000/docs and test interactively.

---

## Troubleshooting

**Issue**: NLTK punkt model not found  
**Fix**: Run `python -c "import nltk; nltk.download('punkt')"`

**Issue**: PyMuPDF import error on Apple Silicon  
**Fix**: Try `pip install --upgrade pymupdf` or use pypdf fallback

**Issue**: Rate limit errors  
**Fix**: Check Gemini API quota with `curl http://localhost:8000/api/v1/metrics`

---

## Next Steps

1. Add document deletion endpoint (DELETE `/api/v1/documents/{id}`)
2. Implement batch upload (accept multiple files)
3. Add admin subject management (POST `/api/v1/admin/subjects`)
4. Implement streaming progress for large files
5. Add document versioning support

---

## Reference

- **OpenAPI Spec**: `specs/002-doc-ingestion/contracts/ingest-api.yaml`
- **Data Model**: `specs/002-doc-ingestion/data-model.md`
- **Research**: `specs/002-doc-ingestion/research.md`
- **Architecture Review**: `specs/002-doc-ingestion/design/architecture-review.md`

**Estimated Complexity**: ⭐⭐⭐ (Moderate)  
**Implementation Time**: 4-6 hours  
**Testing Time**: 2-3 hours  
**Total**: 6-9 hours

---

**END OF QUICKSTART GUIDE**
