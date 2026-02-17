# CourseFlow Frontend Development Guide

## Architecture Overview
- `App.jsx`: Orchestrates session restore, streaming flow, and error handling
- `components/`: UI surfaces (history, input, messages, empty/error states)
- `hooks/`: State hooks (`useChat`, `useStreamingResponse`, `useLocalStorage`)
- `api/`: HTTP client + query endpoints
- `utils/`: Validation, storage, UUID, error mapping

## Streaming Data Flow
1. `ChatInput` submits text
2. `postQuery()` sends `POST /api/v1/query/stream` with `{ query, conversation_id? }`
3. `useStreamingResponse.parseSSEStream()` consumes SSE lines
4. `chunk` updates assistant message progressively
5. `sources` attaches source names
6. `done` finalizes message and updates `conversation_id`

## State & Persistence
- Chat messages + `conversation_id` kept in `useChat`
- Session persisted in localStorage using `saveSession`
- Restored on mount via `loadSession`
- `New Chat` clears in-memory and local storage state

## Styling System
- Editorial clean visual direction (neutral palette, serif display title)
- Tailwind utilities with custom CSS animations in `index.css`
- Responsive behavior validated at 375px / 768px / 1280px

## Test Strategy
- Unit tests: core components + hooks + API utilities
- Integration: full chat scenario with mocked streaming hook
- E2E placeholder: `e2e/chat.spec.js` for Playwright migration

## Commands
```bash
npm run dev
npm run build
npm run lint
npm test
npm run test:cov
```
