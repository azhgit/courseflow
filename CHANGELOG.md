# Changelog

## 004-streaming-responses

- Added `POST /api/v1/query/stream` SSE endpoint for incremental answer delivery.
- Added structured SSE event types: `chunk`, `sources`, `done`, `error`.
- Added streaming error handlers for no relevant docs, rate limit, and timeout paths.
- Added streaming conversation persistence service for chunk reconstruction and turn save.
- Added `/api/v1/metrics` endpoint for lightweight streaming counters and latency gauge.
- Added integration/E2E/unit tests for streaming, persistence, latency, and compatibility.
- No breaking changes for existing `POST /api/v1/query`.

