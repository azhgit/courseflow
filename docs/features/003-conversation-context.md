# 003 - Multi-turn Conversation Context

## Summary
This feature adds conversation continuity so users can ask follow-up questions without repeating prior context.

## Key Capabilities
- Optional `conversation_id` on query requests.
- Auto-create conversation when `conversation_id` is omitted or null.
- Persist user/assistant turns in SQLite.
- Include recent history in prompt context.
- Token-budget-based history trimming (older turns removed first).
- UUID4 conversation identifiers.

## Primary API
- `POST /api/v1/query` (with optional `conversation_id`)

## How It Works
1. Resolve conversation (create new or load existing).
2. Fetch recent turns for context.
3. Apply token budget / turn limit.
4. Execute normal RAG retrieval + generation.
5. Persist completed turn and return `conversation_id`.

## Test Guide
### Automated
```bash
pytest tests/unit -v
pytest tests/integration -v
```

### Manual Smoke Test
1) First query (no conversation id):
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How do async functions work in Python?"}'
```
2) Follow-up query (reuse returned `conversation_id`):
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What about error handling?","conversation_id":"<UUID>"}'
```
Expected: second answer reflects prior context.

## Success Signals
- Follow-up quality improves with context.
- New conversation is created automatically when needed.
- Invalid `conversation_id` returns a clear 404-style error.
