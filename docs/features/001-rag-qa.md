# 001 - Basic RAG Question Answering

## Summary
This feature delivers the core CourseFlow experience: users send a question, the system retrieves relevant knowledge chunks from ChromaDB, and Gemini generates a grounded answer.

## Key Capabilities
- Query endpoint for single-turn Q&A.
- Retrieval with fixed top-k (`k=3`) and similarity threshold (`>= 0.5`).
- Answer generation constrained by retrieved content.
- Clear error handling for empty queries and no relevant documents.
- Basic request quota enforcement (15 requests/minute).

## Primary API
- `POST /api/v1/query`

## How It Works
1. Validate query input.
2. Embed query and search vector store.
3. Filter by similarity threshold.
4. Generate answer from retrieved chunks.
5. Return answer + source references + metadata.

## Test Guide
### Automated
```bash
pytest tests/unit -v
pytest tests/integration -v
```

### Manual Smoke Test
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is photosynthesis?"}'
```
Expected:
- HTTP 200
- Non-empty `answer`
- `sources` returned

### Negative Cases
- Empty query should return HTTP 400.
- Unrelated query should return a clear "no relevant information" error.

## Success Signals
- Valid queries return within ~3 seconds.
- Responses cite retrieved documents.
- No hallucination-style answer when retrieval has no valid chunks.
