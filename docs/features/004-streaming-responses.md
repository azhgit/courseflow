# 004 - Streaming Responses (SSE)

## Summary
This feature introduces Server-Sent Events streaming so answers appear progressively instead of waiting for full completion.

## Key Capabilities
- New streaming endpoint: `POST /api/v1/query/stream`.
- Incremental answer chunks (`chunk` events).
- Structured terminal events (`sources`, `done`, `error`).
- Early validation for empty/whitespace queries.
- Stream-safe error behavior (including mid-stream rate-limit handling).
- Conversation persistence compatibility.

## Event Contract
- `chunk`: incremental answer text
- `sources`: source list
- `done`: completion marker + metadata
- `error`: structured failure payload

## Test Guide
### Automated
```bash
pytest tests/unit -v
pytest tests/integration -v
pytest tests/e2e -v
```

### Manual Smoke Test
```bash
curl -N -X POST "http://localhost:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain photosynthesis step by step"}'
```
Expected:
- First chunk arrives quickly.
- Multiple `chunk` events before completion.
- `sources` then `done` at end.

### Failure Cases
- Empty query -> HTTP 400 before stream start.
- No relevant documents -> stream emits `error` and closes cleanly.

## Success Signals
- Perceived latency significantly improved.
- No broken stream states for common failures.
