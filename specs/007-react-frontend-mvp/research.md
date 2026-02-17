# Research Findings: React Chat Interface MVP

**Session Date**: 2026-02-17  
**Feature**: 007-react-frontend-mvp  
**Status**: Phase 0 Research Complete

---

## Resolved Unknowns

### 1. Server-Sent Events (SSE) Implementation via ReadableStream

**Decision**: Use native ReadableStream API with text decoder for SSE parsing

**Rationale**:
- Native browser API (no external dependencies)
- Better performance than external SSE libraries
- Can handle streaming chunks directly from fetch response
- Aligns with spec constraint: "no external SSE libraries"

**Implementation Pattern**:
```javascript
const response = await fetch(`${apiBase}/api/v1/query`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question, conversation_id })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  buffer += decoder.decode(value);
  const lines = buffer.split('\n');
  buffer = lines.pop(); // Keep incomplete line
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      // Handle event: { type: 'chunk', data: '...' }
    }
  }
}
```

**Error Handling**:
- Network failure: AbortController + timeout
- Stream interrupted: Retry with last conversation_id
- Invalid JSON: Log + show "Connection error, try again"

**Alternatives Considered**:
- EventSource API: Not suitable for POST requests
- Socket.io: Overkill for MVP, adds dependency
- Polling: Too inefficient for demo experience

---

### 2. localStorage Quota Management

**Decision**: Detect quota exceeded, gracefully fall back to in-memory only

**Rationale**:
- localStorage typical quota: 5-10MB per origin
- Chat messages are small (avg 1-5KB each)
- Most demo sessions won't exceed quota
- Graceful fallback maintains UX

**Detection Pattern**:
```javascript
const canUseStorage = () => {
  try {
    const test = '__test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch (e) {
    return e.name === 'QuotaExceededError';
  }
};
```

**Storage Schema**:
```javascript
localStorage.setItem('courseflow_session', JSON.stringify({
  conversation_id: 'uuid-4-string',
  messages: [
    { id: 'uuid', role: 'user', content: '...', timestamp, status: 'complete' },
    { id: 'uuid', role: 'assistant', content: '...', sources: [...], timestamp, status: 'complete' }
  ],
  created_at: '2026-02-17T...',
  updated_at: '2026-02-17T...'
}));
```

**Quota Estimate**:
- Each message: ~500 bytes (conservative)
- Typical demo session: 5-10 messages = 2.5-5KB
- Quota headroom: Safe for 1000+ messages per session

**Fallback**:
- If quota exceeded: Log warning, keep in-memory only
- On refresh: Restore from memory if available, else show empty state
- User doesn't need to know quota failed (transparent)

**Alternatives Considered**:
- IndexedDB: Overkill, more complex API
- Session storage: Lost on refresh (violates SC-008)
- Backend persistence: Out of scope, adds server load

---

### 3. Conversation Lifecycle Management

**Decision**: Generate new conversation_id on page load or "New Chat"; reuse for multi-turn

**Rationale**:
- Simplifies state management (single conversation per session)
- Avoids multi-tab sync issues (each tab is independent)
- Aligns with clarified requirement: "single-browser-session scope"

**Lifecycle**:
```
Page Load:
  ├─ Try restore from localStorage
  │  ├─ Found: Use existing conversation_id
  │  └─ Not found: Request new from backend (/api/v1/query first message)
  │
Send Message:
  ├─ If no conversation_id: Request new from backend, get ID in response
  └─ If conversation_id exists: Include in request for continuity
  
New Chat Button:
  ├─ Clear messages from memory + localStorage
  ├─ Clear conversation_id
  └─ Show empty state again
  
Page Refresh:
  ├─ Restore conversation_id + messages from localStorage
  └─ User can continue conversation seamlessly
```

**Backend Contract**:
- First message: `POST /api/v1/query { question, conversation_id: null }`
- Backend returns: `{ conversation_id: 'uuid', ...stream... }`
- Subsequent: `POST /api/v1/query { question, conversation_id: 'uuid' }`

**Multi-Tab Behavior**:
- Each browser tab is independent (not synced)
- localStorage update triggers are per-tab
- Last write wins if both tabs write simultaneously (acceptable for demo)

**Alternatives Considered**:
- Persistent backend sessions: Requires user auth (out of scope)
- Shared localStorage across tabs: Race conditions, too complex
- Service Worker sync: Overkill for demo MVP

---

### 4. Vite Environment Variables Setup

**Decision**: Use `VITE_*` prefix with .env files for dev/prod config

**Rationale**:
- Vite convention: Only `VITE_*` variables exposed to client code
- Security: Prevents accidental secret leaks
- Flexibility: Different URLs for dev (localhost) vs prod (Zeabur)
- No build-time secrets needed for this feature

**Files**:
```
.env (default, used in dev and build if others not present)
  VITE_API_BASE_URL=http://localhost:8000

.env.production (used during `npm run build` for production)
  VITE_API_BASE_URL=https://api.demo.courseflow.app

.env.development (optional, explicit dev config)
  VITE_API_BASE_URL=http://localhost:8000
```

**Usage in Code**:
```javascript
// api.js
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const fetchQuery = (question, conversationId) => {
  return fetch(`${API_BASE}/api/v1/query`, {
    method: 'POST',
    body: JSON.stringify({ question, conversation_id: conversationId })
  });
};
```

**Build Configuration** (vite.config.js):
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    __API_BASE__: JSON.stringify(process.env.VITE_API_BASE_URL || 'http://localhost:8000')
  }
});
```

**Deployment** (Zeabur, Vercel, etc.):
- Set environment variable: `VITE_API_BASE_URL=https://api.courseflow.app`
- Build step automatically substitutes value
- No secrets exposed in built code

**Alternatives Considered**:
- Runtime config file: Slower to load, complexity
- Direct hardcoded URLs: Not flexible for prod
- API discovery: Over-engineered for MVP

---

## Technology Dependencies (Resolved Versions)

| Package | Version | Reason | Constraint |
|---------|---------|--------|-----------|
| React | 18.2.0+ | Latest stable, good SSR support | Minimum 18.0 |
| React-DOM | 18.2.0+ | Pairs with React | Minimum 18.0 |
| Vite | 5.0.0+ | Latest build tool | Minimum 4.0 |
| Tailwind CSS | 3.3.0+ | Latest with JIT | Minimum 3.0 |
| @vitejs/plugin-react | 4.0.0+ | React plugin for Vite | Latest |

**No additional external dependencies for SSE, localStorage, or fetch** — all native APIs.

---

## Performance Considerations

### Bundle Size Target
- Gzipped React app: <150KB (React 18 + Tailwind)
- Tailwind CSS (purged): ~30KB gzipped
- App code: <20KB gzipped
- **Total**: <200KB gzipped ✅ Acceptable for demo

### Load Time Breakdown
| Metric | Target | How to Validate |
|--------|--------|-----------------|
| FCP (First Contentful Paint) | <1s | Lighthouse, DevTools |
| LCP (Largest Contentful Paint) | <2s | Lighthouse, DevTools |
| CLS (Cumulative Layout Shift) | <0.1 | Lighthouse |
| TTI (Time to Interactive) | <3s | Lighthouse |

### SSE Streaming Performance
- First chunk latency: <1.5s (SC-001)
- Per-chunk processing: <100ms
- Message rendering: <50ms per message

---

## Testing Strategy Details

### Unit Tests (Jest + React Testing Library)
- `useChat` hook: message handling, conversation ID management
- `useLocalStorage` hook: storage, quota detection, fallback
- `useStreamingResponse` hook: SSE parsing, error handling
- Utility functions: error mapping, message validation

### Integration Tests
- Chat flow: input → send → stream → display → storage
- localStorage persistence: write → refresh → restore
- Error scenarios: 429, 503, network failure, parsing error

### E2E Tests (Playwright or Cypress)
- Full user journey: load page → send question → verify sources → refresh → verify history
- Keyboard navigation: Tab + Enter submission
- Responsive layout: 375px and 1280px viewports
- Error message display: correct message for each error type

### Manual Tests (QA)
- Demo experience: streaming fluidity, UX responsiveness
- Mobile usability: touch interactions, readability
- Browser compatibility: Chrome, Firefox, Safari (latest versions)

---

## Acceptance Criteria Mapping

| SC | Research Finding | Implementation Strategy |
|----|------------------|------------------------|
| SC-001 | First chunk <1.5s | ReadableStream parsing optimized, no debouncing |
| SC-002 | Smooth streaming | Chunk rendering with requestAnimationFrame |
| SC-003 | Sources below answer | Source rendering in stream handler |
| SC-004 | New Chat resets | Clear localStorage + state on button click |
| SC-005 | Error messages exact | Map error type to exact message string |
| SC-006 | 375px-1280px usable | Tailwind responsive classes + manual testing |
| SC-007 | <60s full flow | Optimized bundle, no lazy loading for critical paths |
| SC-008 | 100% history restore | localStorage serialization, refresh handler |
| SC-009 | Cache hits on examples | Load examples from Feature 006 API |

---

## Next Actions

1. ✅ **Phase 0**: Research complete
2. 🟡 **Phase 1**: Design artifacts
   - [ ] Generate data-model.md
   - [ ] Generate contracts/query-streaming.md
   - [ ] Document component architecture
3. 🔲 **Phase 2**: Task generation (tasks.md)
4. 🔲 **Phase 3**: Implementation

**Ready to proceed to Phase 1 Design** ✅
