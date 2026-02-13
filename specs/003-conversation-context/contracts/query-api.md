# API Contract: Multi-turn Conversation Support

**Feature**: 003-conversation-context | **Date**: 2026-02-13  
**Endpoint**: `POST /api/v1/query` (modified)  
**Purpose**: Extend existing query endpoint to support multi-turn conversations

---

## Overview

This contract extends the existing RAG query endpoint to support stateful conversations. The endpoint remains backward compatible: existing clients can continue sending queries without `conversation_id` and will now receive a generated `conversation_id` in responses for optional follow-up use.

**Key Changes**:
- Request accepts optional `conversation_id` (UUID4 string or null)
- Response always includes `conversation_id` (generated if not provided)
- New error: 404 for invalid/non-existent conversation_id

---

## Endpoint Specification

### POST /api/v1/query

**Description**: Execute RAG query with optional conversation context

**Authentication**: None (v1)

**Rate Limiting**: Existing (15 RPM global limit, inherited from Gemini quota)

**Request Headers**:
```
Content-Type: application/json
```

**Request Body Schema**:
```json
{
  "query": "string (required, 1-1000 characters)",
  "conversation_id": "string | null (optional, UUID4 format)",
  "subject": "string (optional, existing parameter)"
}
```

**Response Schema (Success - 200 OK)**:
```json
{
  "success": true,
  "data": {
    "answer": "string",
    "sources": ["string"],
    "conversation_id": "string (UUID4)"
  }
}
```

---

## Example Requests

### Example 1: New Conversation
```http
POST /api/v1/query

{
  "query": "How do async functions work?"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "answer": "Async functions...",
    "sources": ["python-async.md"],
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Example 2: Follow-up Query
```http
POST /api/v1/query

{
  "query": "What about error handling?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "answer": "For error handling...",
    "sources": ["python-async.md", "python-exceptions.md"],
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## Error Responses

| HTTP Status | error | Client Action |
|-------------|-------|---------------|
| 400 | `validation_error` | Fix request and retry |
| 404 | `conversation_not_found` | Retry with null conversation_id |
| 500 | `internal_error` | Retry with same request |

---

See full specification for performance characteristics, OpenAPI schema, and testing checklist.
