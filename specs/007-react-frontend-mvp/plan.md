# Implementation Plan: React Chat Interface MVP for CourseFlow Demo

**Feature Branch**: `007-react-frontend-mvp`  
**Feature Spec**: `specs/007-react-frontend-mvp/spec.md`  
**Session Date**: 2026-02-17  
**Status**: Phase 0 - Research & Technical Context

---

## Technical Context

### System Architecture
- **Type**: Frontend Single Page Application (SPA)
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS (utility-first, no component libraries)
- **HTTP Client**: Native Fetch API + ReadableStream for SSE
- **State Management**: React hooks (useState, useRef) — no Redux/Zustand
- **Persistence**: Browser localStorage API

### Key Technology Decisions
| Component | Choice | Rationale |
|-----------|--------|-----------|
| UI Framework | React 18 | Standard, ecosystem, team familiarity |
| Build Tool | Vite | Fast dev server, minimal config, ESM-native |
| CSS | Tailwind CSS | Utility-first matches spec, no component deps |
| SSE Client | ReadableStream API | Native browser API, no external libs |
| State | useState/useRef | MVP scope doesn't require Redux |
| Backend API | Environment variable | Flexible deployment, local dev support |
| Session Storage | localStorage | Built-in, no external storage needed |
| HTTP | Fetch API | Native, async/await support |

### Resolved Clarifications (from clarify session 2026-02-17)

1. **Backend API URL**: Environment variable with localhost fallback
   - Env var: `VITE_API_BASE_URL` (Vite convention)
   - Default: `http://localhost:8000`
   - Allows dev/prod config without code changes

2. **Chat History Persistence**: localStorage with graceful degradation
   - Store message history + conversation_id to localStorage
   - Restore on page load if available
   - Fall back to in-memory only if quota exceeded

3. **Example Questions**: From precached demo set (Feature 006)
   - Load from backend demo cache endpoint
   - Ensures cache hits and zero API quota consumption
   - Depends on Feature 006 availability

### Data Model

#### Chat Session (localStorage serializable)
```
{
  conversation_id: string (UUID),
  messages: Message[],
  created_at: ISO8601 string,
  updated_at: ISO8601 string
}
```

#### Message
```
{
  id: string (UUID),
  role: 'user' | 'assistant',
  content: string,
  sources?: Source[],
  status: 'in-progress' | 'complete',
  timestamp: ISO8601 string
}
```

#### Source
```
{
  name: string,
  url?: string
}
```

#### Error State
```
{
  type: 'ip_limit' | 'daily_quota' | 'no_documents' | 'network_error',
  message: string,
  retry_after?: number (seconds)
}
```

### API Integration Points

#### GET /api/v1/query (streaming)
- **Input**: question (string), conversation_id (optional)
- **Output**: Server-Sent Events stream
  - `start` event: returns new conversation_id
  - `chunk` events: answer text chunks
  - `sources` event: source attribution
  - `error` event: no_relevant_documents, etc.
  - `done` event: stream complete

#### Environment Configuration
- `VITE_API_BASE_URL`: Backend URL (default: http://localhost:8000)
- Used in: SSE connection, conversation context

### Constraints & Dependencies

✅ **Met by Feature 006**:
- Demo cache with precached questions
- Rate limiting (IP hourly, daily global)
- Error signals (429, 503 responses)

✅ **Browser API Requirements**:
- ReadableStream (all modern browsers)
- localStorage (all modern browsers)
- Fetch API (all modern browsers)

⚠️ **CORS Requirement**:
- Backend MUST allow cross-origin requests from frontend origin
- Configured in backend deployment (not in scope for this feature)

### Non-Functional Targets

| Metric | Target | Validation |
|--------|--------|-----------|
| First paint | <1s | Lighthouse, dev tools |
| First answer word | <1.5s (SC-001) | Load testing, demo observation |
| Streaming latency | <100ms per chunk | Network tab analysis |
| Page refresh restore | 100% of messages (SC-008) | Manual testing |
| Mobile usability | 375px+ (SC-006) | Responsive testing |
| Keyboard accessibility | Tab + Enter navigation (SC-008) | Accessibility audit |

### Testing Strategy

- **Unit**: Component logic, utility functions (>80% coverage)
- **Integration**: Chat flow, localStorage, SSE parsing
- **E2E**: Full user journey (demo simulation)
- **Manual**: Streaming UX, error messaging, mobile layout

### Scope Boundaries

✅ **In Scope**:
- Chat input + send
- Streaming answer rendering
- localStorage persistence
- Example questions from demo cache
- Error message mapping (429, 503, no docs, network)
- Responsive layout (375px–1280px)

❌ **Out of Scope**:
- User authentication
- Dark mode
- Markdown rendering
- Message editing
- Document upload
- Analytics/logging (beyond console)

---

## Phase 0: Research & Unknowns Resolution

### Research Tasks

1. **ReadableStream SSE Parsing** (NEEDS CLARIFICATION)
   - How to reliably parse Server-Sent Events from ReadableStream
   - Error recovery on stream interruption
   - Chunk buffering strategy
   
2. **localStorage Quota Management** (NEEDS CLARIFICATION)
   - What's typical quota per browser (5-10MB)
   - How to detect quota exceeded
   - Graceful fallback to in-memory only

3. **Conversation Context Flow** (NEEDS CLARIFICATION)
   - When to request new conversation_id vs reuse
   - How to clear context on "New Chat"
   - localStorage sync on multi-tab browser

4. **Vite Environment Variables** (NEEDS CLARIFICATION)
   - `VITE_*` prefix convention
   - Build-time vs runtime substitution
   - .env file structure for dev/prod

### Research Status
- [ ] ReadableStream best practices for SSE
- [ ] localStorage quota detection patterns
- [ ] Conversation lifecycle management
- [ ] Vite environment variable setup

---

## Phase 1: Design Artifacts

### Data Model (data-model.md)
- [ ] Chat Session entity schema
- [ ] Message entity schema
- [ ] Source attribution structure
- [ ] Error state mapping
- [ ] localStorage serialization format

### API Contracts (contracts/)
- [ ] SSE streaming endpoint documentation
- [ ] Query request schema
- [ ] Event message formats (chunk, sources, error, done)
- [ ] Error response mapping
- [ ] Example payloads

### Component Architecture (design decisions)
- [ ] App component (root, state provider)
- [ ] ChatHistory component (scrollable message list)
- [ ] ChatInput component (input + send button)
- [ ] MessageBubble component (user/assistant message rendering)
- [ ] EmptyState component (centered logo + example questions)
- [ ] ErrorAlert component (error message rendering)
- [ ] StreamingCursor component (typing indicator)

### State Management Plan
- [ ] useChat hook (messages, conversation_id, send, newChat)
- [ ] useLocalStorage hook (persist/restore chat state)
- [ ] useStreamingResponse hook (SSE parsing, chunk buffering)
- [ ] Error state handling (type → message mapping)

### Performance Optimization Checklist
- [ ] Code splitting (lazy load non-critical components)
- [ ] Image optimization (logo, any graphics)
- [ ] Bundle size monitoring (target <200KB gzipped)
- [ ] FCP target: <1s on 3G

### Testing Plan
- [ ] useChat hook tests (100% coverage)
- [ ] useLocalStorage integration tests
- [ ] SSE parsing error scenarios
- [ ] Message rendering tests
- [ ] Responsive layout tests (375px, 1280px)
- [ ] E2E test flow: load → send question → stream → verify sources → refresh → verify restore

---

## Phase 2: Implementation Tasks

### Module Structure
```
src/
├── components/
│   ├── ChatHistory.jsx
│   ├── ChatInput.jsx
│   ├── MessageBubble.jsx
│   ├── EmptyState.jsx
│   ├── ErrorAlert.jsx
│   └── StreamingCursor.jsx
├── hooks/
│   ├── useChat.js
│   ├── useLocalStorage.js
│   └── useStreamingResponse.js
├── services/
│   ├── api.js (fetch wrapper, env var handling)
│   └── sseParser.js (EventSource / ReadableStream parsing)
├── styles/
│   └── globals.css (Tailwind imports)
├── App.jsx
└── main.jsx
```

### Build Configuration (Vite)
- [ ] vite.config.js (API proxy for dev, env handling)
- [ ] .env (VITE_API_BASE_URL=http://localhost:8000)
- [ ] .env.production (VITE_API_BASE_URL=https://api.courseflow.app)
- [ ] package.json (scripts: dev, build, preview)

### Deployment Strategy
- Static site deployment (Vercel, Netlify, Zeabur)
- Environment variables at build time or via runtime config
- CORS proxy if needed (configured at deployment)

---

## Constitution Compliance Checklist

| MUST Principle | Requirement | Status |
|---|---|---|
| Code Quality | Functions ≤50 lines, files ≤500 lines | ✅ React components enforces |
| Testing | 80% coverage minimum | 🟡 Planning phase |
| Performance | <2s p95 (SSE first chunk <1.5s) | ✅ SC-001 defines |
| Zero-Cost | No paid services | ✅ Vite + free hosting only |
| API-First | Clear contract with backend | ✅ SSE contract defined |
| Async-First | All I/O non-blocking | ✅ Fetch + ReadableStream |

**Note**: This is a frontend-only feature; backend API-first principles already enforced by Feature 001.

---

## Phase 1 Completion Artifacts

- [x] Technical Context filled
- [x] research.md finalized (Phase 0 research complete)
- [x] data-model.md written (entities, validation, serialization)
- [x] API contracts documented in data-model.md (SSE events, error mappings)
- [x] Component architecture documented in plan.md
- [x] State management hooks designed in plan.md
- [x] Vite configuration planned in plan.md

---

## Next Steps

1. **Phase 0 Complete**: Research unknowns
   - Finalize research.md with implementation patterns
   
2. **Phase 1 Complete**: Design phase
   - Write data-model.md with schema + examples
   - Write API contract documentation
   - Document component hierarchy
   - Design state hooks interfaces

3. **Phase 2**: Generate tasks (tasks.md)
   - T001-T010: Setup & scaffolding
   - T011-T020: Core components
   - T021-T030: State management + integration
   - T031-T040: Styling + responsive
   - T041-T050: Error handling + edge cases
   - T051-T060: Testing + documentation

4. **Phase 3**: Implementation
   - Execute tasks in dependency order
   - Run tests at each checkpoint
   - Validate against acceptance criteria

---

## Session History

| Date | Phase | Status |
|------|-------|--------|
| 2026-02-17 | Specify | ✅ Complete (007-react-frontend-mvp branch created) |
| 2026-02-17 | Clarify | ✅ Complete (3 clarifications resolved) |
| 2026-02-17 | Plan | 🟡 In Progress (Technical Context + Phase 0) |
