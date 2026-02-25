# 007 - React Chat Frontend MVP

## Summary
This feature delivers a public chat UI for CourseFlow demos with streaming UX, conversation continuity, and user-friendly error handling.

## Key Capabilities
- Public chat page with prompt input and message timeline.
- Progressive streaming answer rendering.
- Loading/searching status before first chunk.
- Source display below completed assistant messages.
- Multi-turn continuity with persisted `conversation_id`.
- LocalStorage session restore after refresh.
- Demo-safe error messages (rate limit, no content, network).

## UI Behaviors to Verify
- Enter key and Send button both submit.
- "New Chat" resets conversation.
- Empty state shows example prompts.
- Typing cursor appears while streaming and disappears on completion.

## Test Guide
### Automated
```bash
pytest tests -v
```

### Manual Smoke Test
1) Open frontend page.
2) Submit a question and observe incremental response.
3) Ask a follow-up and verify conversation continuity.
4) Refresh browser and verify history restoration.

### Error Cases
- Simulate quota exceeded and verify user-facing message.
- Simulate network failure and verify retry-oriented feedback.

## Success Signals
- Smooth real-time demo experience.
- Clear behavior on both success and error paths.
- Mobile and desktop usability for interview scenarios.
