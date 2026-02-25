# 002 - Document Ingestion and Knowledge Base Management

## Summary
This feature enables administrators to upload documents into the knowledge base so they become searchable by the RAG pipeline.

## Key Capabilities
- Upload support for `.md`, `.txt`, and `.pdf`.
- Input validation (file type, size, empty files).
- Semantic chunking with sentence integrity priority.
- Embedding generation and vector persistence.
- Idempotent duplicate protection using normalized-content hash.
- Subject tagging for filtered retrieval.
- Retry behavior for transient processing failures.

## Primary API
- `POST /api/v1/ingest`
- `GET /api/v1/documents`
- `GET /api/v1/subjects`

## How It Works
1. Validate file and metadata.
2. Extract text and normalize content.
3. Create semantic chunks (target token range while preserving sentence boundaries).
4. Generate embeddings.
5. Store chunks + metadata in ChromaDB.
6. Return ingestion summary.

## Test Guide
### Automated
```bash
pytest tests/unit -v
pytest tests/integration -v
```

### Manual Smoke Test
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@docs/biology/photosynthesis.md" \
  -F 'metadata={"subject":"biology"}'
```
Expected:
- HTTP 200
- Chunk count in response
- Newly ingested content queryable via `/api/v1/query`

### Validation Cases
- Upload same content twice -> second upload should be skipped/deduplicated.
- Invalid file type -> HTTP 400 with clear reason.

## Success Signals
- Uploaded documents become retrievable quickly.
- Duplicate uploads do not pollute search results.
- Subject filtering behaves consistently.
