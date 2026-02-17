# Implementation Tasks: React Chat Interface MVP for CourseFlow Demo

**Feature**: 007-react-frontend-mvp  
**Feature Spec**: `specs/007-react-frontend-mvp/spec.md`  
**Created**: 2026-02-17  
**Total Tasks**: 58  
**Status**: Ready for implementation

---

## Task Overview

### By User Story
- **User Story 1** (Ask and receive streamed answers): 18 tasks (T016-T033)
- **User Story 2** (Continue multi-turn conversation): 8 tasks (T034-T041)
- **User Story 3** (Handle demo-safe empty and error states): 10 tasks (T042-T051)
- **Setup & Foundational**: 15 tasks (T001-T015)
- **Polish & Cross-Cutting**: 7 tasks (T052-T058)

### Parallel Execution Opportunities
- **Phase 1** (Setup): All tasks are sequential
- **Phase 2** (Foundational): T005-T015 can run in parallel (separate utilities/hooks)
- **US1 (P1)**: T020-T027 can run in parallel (UI components)
- **US1 (P1)**: T028-T033 must be sequential (integration)
- **US2 (P2)**: T034-T041 can run in parallel (state + storage)
- **US3 (P3)**: T042-T051 mostly parallel except error mapping

### Suggested MVP Scope
**Minimum Viable Product**: Complete User Story 1 (P1)
- Delivers core value: Ask question → See streamed answer
- Achievable in one sprint
- Subsequent stories (P2, P3) enhance robustness

---

## Phase 1: Project Setup & Scaffolding

### Phase Goal
Initialize Vite + React project with all dependencies, configuration files, and base structure.

### Independent Test Criteria
- `npm run dev` starts server at http://localhost:5173
- `npm run build` succeeds with no errors
- All imports resolve correctly
- Vite config recognizes VITE_API_BASE_URL environment variable

---

- [ ] T001 Create Vite React project structure with `npm create vite@latest` at project root (`src/frontend/`)
- [ ] T002 Install core dependencies: React 18.2.0+, Vite 5.0.0+, Tailwind CSS 3.3.0+ in `src/frontend/package.json`
- [ ] T003 Install dev dependencies: @tailwindcss/forms, postcss, autoprefixer, vite in `src/frontend/package.json`
- [ ] T004 Create `src/frontend/.env` with `VITE_API_BASE_URL=http://localhost:8000` for development
- [ ] T005 Create `src/frontend/.env.production` with production API URL for Zeabur deployment
- [ ] T006 Create `src/frontend/vite.config.js` with Vite configuration, React plugin, and API proxy if needed
- [ ] T007 Create `src/frontend/postcss.config.js` for Tailwind CSS processing
- [ ] T008 Create `src/frontend/tailwind.config.js` with responsive design breakpoints (375px min, 1280px max)
- [ ] T009 Create `src/frontend/index.css` with Tailwind directives and global styles
- [ ] T010 Create `src/frontend/public/` directory with favicon and favicon metadata files
- [ ] T011 Create `src/frontend/src/` directory structure: `/components`, `/hooks`, `/utils`, `/styles`, `/api`
- [ ] T012 Create `src/frontend/src/main.jsx` React app entry point with ReactDOM.createRoot mounting
- [ ] T013 Create `src/frontend/src/App.jsx` top-level component skeleton
- [ ] T014 [P] Create utility modules: `src/frontend/src/utils/uuid.js` (UUID v4 generation), `src/frontend/src/utils/validation.js` (session/message validation)
- [ ] T015 [P] Create custom hooks: `src/frontend/src/hooks/useLocalStorage.js` (read/write with quota detection), `src/frontend/src/hooks/useStreamingResponse.js` (SSE parsing skeleton)

---

## Phase 2: Foundational Infrastructure

### Phase Goal
Build core utilities, state management hooks, and API client that all user stories depend on.

### Independent Test Criteria
- UUID generation works and produces valid v4 UUIDs
- localStorage read/write with quota detection works
- Validation functions catch malformed sessions/messages
- API client connects to backend and can be tested with mock SSE
- Environment variables are correctly resolved

---

- [ ] T016 Implement `src/frontend/src/utils/uuid.js` with UUID v4 generation function
- [ ] T017 Implement `src/frontend/src/utils/validation.js` with schema validators (ChatSession, Message, Source, ErrorState)
- [ ] T018 Implement `src/frontend/src/utils/storage.js` with localStorage helpers: loadSession, saveSession, clearSession
- [ ] T019 Implement `src/frontend/src/api/client.js` with Fetch API wrapper: getConfig, buildUrl, makeRequest, handleErrors
- [ ] T020 [P] Implement `src/frontend/src/hooks/useLocalStorage.js` with get, set, remove, and QuotaExceededError handling
- [ ] T021 [P] Implement `src/frontend/src/hooks/useChat.js` (state: conversation_id, messages, isLoading, error; actions: addUserMessage, addAssistantMessage, clearChat, setError)
- [ ] T022 [P] Implement `src/frontend/src/hooks/useStreamingResponse.js` with ReadableStream SSE parsing: parseSSEEvents, handleChunk, handleSources, handleError, handleDone
- [ ] T023 Implement `src/frontend/src/utils/errorMapping.js` with HTTP status → ErrorState mapping (429→ip_limit/daily_quota, stream error→no_documents, network→network_error)
- [ ] T024 Create test file `src/frontend/src/utils/__tests__/validation.test.js` with schema validation tests
- [ ] T025 Create test file `src/frontend/src/hooks/__tests__/useLocalStorage.test.js` with read/write and quota tests
- [ ] T026 Create test file `src/frontend/src/api/__tests__/client.test.js` with API client and error mapping tests

---

## Phase 3: User Story 1 - Ask and Receive Streamed Answers (Priority: P1)

### Phase Goal
Implement core chat interaction: user submits question, system shows search status, answer streams in progressively, sources appear below.

### User Story 1 Acceptance Criteria
1. Question submission via Enter or Send button → added to history, processing starts
2. Between submission and first chunk → "🔍 Searching knowledge base..." status shown
3. Each chunk arrives → assistant message updates progressively (not batched)
4. While streaming → visible "▌" typing cursor at end
5. On stream completion → cursor disappears, sources shown, message marked complete

### Independent Test Criteria
- Open chat page in browser
- Enter any question (e.g., "What is photosynthesis?")
- Submit via Enter key
- Verify status indicator appears within 1s
- Verify chunks arrive and update progressively
- Verify sources appear once complete
- Verify no console errors during streaming

---

- [ ] T027 Create `src/frontend/src/components/App.jsx` with main layout: header, chat history area, input area, "New Chat" button
- [ ] T028 [P] Create `src/frontend/src/components/ChatHistory.jsx` with scrollable message list, auto-scroll to newest message
- [ ] T029 [P] Create `src/frontend/src/components/ChatInput.jsx` with text input field, Send button, Enter key handling, submit validation
- [ ] T030 [P] Create `src/frontend/src/components/MessageBubble.jsx` rendering user/assistant message with content and role styling
- [ ] T031 [P] Create `src/frontend/src/components/StreamingCursor.jsx` with blinking "▌" animation for in-progress messages
- [ ] T032 [P] Create `src/frontend/src/components/SourceAttribution.jsx` displaying "Sources: [Doc 1], [Doc 2]" below completed message
- [ ] T033 [P] Create `src/frontend/src/components/SearchStatus.jsx` showing "🔍 Searching knowledge base..." between submit and first chunk
- [ ] T034 Implement `src/frontend/src/api/query.js` with postQuery(question, conversationId) function calling /api/v1/query endpoint and returning SSE response stream
- [ ] T035 Implement SSE event parsing in `src/frontend/src/hooks/useStreamingResponse.js`: handle start, chunk, sources, done, error events with proper state updates
- [ ] T036 Wire `src/frontend/src/App.jsx` to connect input submission → postQuery → useStreamingResponse → append message to history
- [ ] T037 Ensure streaming updates are non-blocking: chunks append to message content without re-rendering full history
- [ ] T038 Implement message status transitions: user message='complete' on create, assistant message='in-progress' on create→'complete' on 'done' event
- [ ] T039 Test US1 scenario: submit question → verify status appears → verify chunks stream → verify sources appear → verify scrolling works
- [ ] T040 Test US1 edge case: rapid submissions while streaming → queue behavior, previous stream cancellation if new submit occurs
- [ ] T041 Test US1 performance: measure first chunk arrival time, verify <1.5s target (SC-001)

---

## Phase 4: User Story 2 - Continue Multi-turn Conversation (Priority: P2)

### Phase Goal
Maintain conversation context across multiple questions, restore state on page refresh, provide "New Chat" reset.

### User Story 2 Acceptance Criteria
1. User sends follow-up question → system reuses same conversation_id for continuity
2. User clicks "New Chat" → prior history cleared, fresh conversation_id used
3. Page refreshes during active chat → message history and conversation_id restored

### Independent Test Criteria
- Ask first question, note conversation_id in messages
- Ask follow-up question, verify same conversation_id is sent to backend
- Refresh browser, verify all messages are restored
- Click "New Chat", verify history cleared and new conversation_id used next submission
- Check localStorage contains serialized ChatSession

---

- [ ] T042 [P] Implement conversation_id extraction from `start` SSE event in `src/frontend/src/hooks/useStreamingResponse.js`
- [ ] T043 [P] Implement conversation_id reuse logic in `src/frontend/src/api/query.js`: include in subsequent requests if present
- [ ] T044 Implement "New Chat" button handler in `src/frontend/src/App.jsx`: clear messages, clear conversation_id, reset input, show empty state
- [ ] T045 Implement localStorage persistence trigger: after each message completes, save ChatSession to localStorage via useLocalStorage hook
- [ ] T046 Implement page load restoration in `src/frontend/src/App.jsx`: on mount, check localStorage, restore messages and conversation_id if available
- [ ] T047 Create `src/frontend/src/components/NewChatButton.jsx` with confirmation dialog for clearing history
- [ ] T048 Test US2 scenario: send Q1 → send Q2 with same conversation_id → refresh page → verify Q1 and Q2 restored
- [ ] T049 Test US2 edge case: refresh during active streaming → verify partial message is handled gracefully
- [ ] T050 Test localStorage persistence: verify ChatSession schema is valid after save/restore cycle
- [ ] T051 Test multi-turn backend behavior: verify conversation context is maintained across turns via conversation_id

---

## Phase 5: User Story 3 - Handle Demo-Safe Empty and Error States (Priority: P3)

### Phase Goal
Display professional empty state on first load, map error conditions to user-friendly messages, handle quota and network failures.

### User Story 3 Acceptance Criteria
1. Empty state on load: centered logo + 4 example questions from precached set, selectable
2. Rate limit (429 hourly): show "Demo limit reached. Try again in 1 hour."
3. Quota exhausted (429 daily): show "Daily demo limit reached. Resets at midnight."
4. No relevant docs (SSE error): show "No content found for this query. Try rephrasing your question."
5. Network failure: show "Connection lost. Please check your network and try again."

### Independent Test Criteria
- Page loads → empty state shown with 4 example questions
- Click example question → auto-fills input and submits
- Exhaust demo quota (or simulate 429) → verify exact error message shown
- Network disconnects → verify error message and retry button shown
- Error dismissal and recovery → user can submit new question after error

---

- [ ] T052 Create `src/frontend/src/components/EmptyState.jsx` with centered logo/branding and 4 example question buttons
- [ ] T053 [P] Create `src/frontend/src/components/ErrorAlert.jsx` with error type → message mapping and retry/dismiss actions
- [ ] T054 [P] Create `src/frontend/src/api/examples.js` with getExampleQuestions() fetching from /api/v1/demo/examples backend endpoint
- [ ] T055 Implement example questions loading in `src/frontend/src/App.jsx`: fetch on mount, populate EmptyState component
- [ ] T056 Implement error mapping in `src/frontend/src/hooks/useStreamingResponse.js`: HTTP status 429→check body for "daily_quota_exhausted" flag, SSE error event→"no_documents", network→"network_error"
- [ ] T057 Implement error display in `src/frontend/src/App.jsx`: show ErrorAlert when error state is set, provide retry and dismiss actions
- [ ] T058 Test US3 scenario: load page → empty state shown → click example → submits and answers → clear → new empty state
- [ ] T059 Test US3 error handling: simulate each error type (429 hourly, 429 daily, no docs, network) → verify exact message displayed
- [ ] T060 Test US3 recovery: dismiss error → user can submit new question and recover
- [ ] T061 Test example questions: verify all 4 examples load from backend, clicking each auto-fills input correctly

---

## Phase 6: Styling, Responsive Design & Polish

### Phase Goal
Apply Tailwind CSS styling for professional appearance, ensure mobile and desktop usability, add polish and animations.

### Independent Test Criteria
- Page renders correctly at 375px viewport (mobile)
- Page renders correctly at 1280px viewport (desktop)
- All interactive elements accessible via keyboard (Tab, Enter, Escape)
- Message scrolling smooth and responsive
- No layout shift or FOUC (Flash of Unstyled Content)
- Animations smooth at 60fps

---

- [x] T062 [P] Style `src/frontend/src/components/App.jsx` layout: header, main chat area, input footer with Tailwind responsive classes
- [x] T063 [P] Style `src/frontend/src/components/ChatHistory.jsx`: scrollable container, proper spacing, auto-scroll behavior
- [x] T064 [P] Style `src/frontend/src/components/ChatInput.jsx`: input field, send button, keyboard focus states
- [x] T065 [P] Style `src/frontend/src/components/MessageBubble.jsx`: user message (right-align, blue bg), assistant (left-align, gray bg), readable font sizing
- [x] T066 [P] Style `src/frontend/src/components/StreamingCursor.jsx`: blinking animation using Tailwind or CSS keyframes
- [x] T067 [P] Style `src/frontend/src/components/SourceAttribution.jsx`: gray italic text, readable line-height
- [x] T068 [P] Style `src/frontend/src/components/EmptyState.jsx`: centered logo, grid of example buttons, hover states
- [x] T069 [P] Style `src/frontend/src/components/ErrorAlert.jsx`: prominent error styling, dismiss button
- [x] T070 Implement responsive testing at 375px, 768px, 1280px breakpoints in `src/frontend/src/index.css`
- [x] T071 Ensure keyboard navigation works: Tab through input/button, Enter to send, Escape to dismiss error
- [x] T072 Add subtle animations: message fade-in, streaming cursor blink, error slide-down
- [x] T073 Optimize bundle: run `npm run build` and verify output is <200KB gzipped
- [ ] T074 Test mobile UX: scroll, input focus, touch interactions on actual device or simulator

---

## Phase 7: Testing & Documentation

### Phase Goal
Write test suites for core functionality, create user documentation, and validate all acceptance criteria.

### Test Strategy
- **Unit Tests**: Hooks, utilities, validation (~30 tests)
- **Integration Tests**: API client + storage + components (~15 tests)
- **E2E Tests**: Full chat flows, error scenarios (~10 tests)
- **Manual Tests**: Streaming UX, mobile layout, accessibility

---

- [x] T075 Create `src/frontend/src/components/__tests__/ChatHistory.test.jsx` with message rendering and scroll tests
- [x] T076 Create `src/frontend/src/components/__tests__/ChatInput.test.jsx` with submit, Enter key, and validation tests
- [x] T077 Create `src/frontend/src/components/__tests__/MessageBubble.test.jsx` with role-based styling tests
- [x] T078 Create `src/frontend/src/hooks/__tests__/useChat.test.js` with message add/clear operations
- [x] T079 Create `src/frontend/src/hooks/__tests__/useStreamingResponse.test.js` with SSE event parsing tests
- [x] T080 Create `src/frontend/src/api/__tests__/query.test.js` with API request/response tests
- [x] T081 Create integration test `src/frontend/src/__tests__/integration/chatFlow.test.jsx` with full user scenario
- [x] T082 Create E2E test script `src/frontend/e2e/chat.spec.js` with Playwright/Cypress for full browser flow
- [x] T083 Create `src/frontend/README.md` with setup, development, and build instructions
- [x] T084 Create `src/frontend/DEVELOPMENT.md` with architecture overview, component structure, API integration
- [x] T085 Run test suite: `npm test` and verify coverage >80% (33 tests passing, 82.64% statements)
- [x] T086 Run linter: `npm run lint` and fix all issues
- [ ] T087 Manual acceptance test: All 9 success criteria (SC-001 through SC-009) verified

---

## Phase 8: Deployment & Final Validation

### Phase Goal
Prepare frontend for deployment to Zeabur, validate against all success criteria, document deployment process.

### Success Criteria Coverage
- **SC-001**: First word <1.5s (load test + demo observation)
- **SC-002**: Smooth streaming (manual observation + network tab analysis)
- **SC-003**: Sources below answer (manual verification)
- **SC-004**: New Chat resets (manual test)
- **SC-005**: Exact error messages (error scenario testing)
- **SC-006**: 375px-1280px usable (responsive testing)
- **SC-007**: <60s end-to-end (stopwatch test)
- **SC-008**: 100% history restore (localStorage test)
- **SC-009**: Cache hits on examples (analytics/logging)

---

- [ ] T088 Create `src/frontend/.env.production` for Zeabur with production API base URL
- [ ] T089 Configure build output: verify `src/frontend/dist/` is created and contains `index.html`, CSS, JS bundles
- [ ] T090 Create deployment documentation `src/frontend/DEPLOY.md` with Zeabur build/deploy steps
- [ ] T091 Test production build: `npm run build && npm run preview` and verify app works at preview URL
- [ ] T092 Performance audit: run Lighthouse on production build, target Core Web Vitals
- [ ] T093 CORS validation: test from deployed frontend URL to backend, verify no CORS errors
- [ ] T094 Manual SC-001 test: submit question, measure time to first word, verify <1.5s
- [ ] T095 Manual SC-002 test: observe streaming updates, verify smooth and not batched
- [ ] T096 Manual SC-003 test: verify sources appear below completed answer
- [ ] T097 Manual SC-004 test: click "New Chat", verify history cleared and input reset
- [ ] T098 Manual SC-005 test: trigger each error condition, verify exact message shown
- [ ] T099 Manual SC-006 test: resize viewport to 375px and 1280px, verify usable in both
- [ ] T100 Manual SC-007 test: time full flow from page load to answer complete, verify <60s
- [ ] T101 Manual SC-008 test: with populated chat, refresh page, verify all messages restored
- [ ] T102 Manual SC-009 test: click example questions, verify fast response (cache hits)
- [ ] T103 Deploy to Zeabur staging environment
- [ ] T104 Smoke test on staging: basic chat flow works, no console errors
- [ ] T105 Promote to Zeabur production
- [ ] T106 Final validation: all acceptance criteria met, feature demo-ready

---

## Dependency Graph

```
Phase 1: Setup (T001-T015)
    ↓ (all tasks must complete)
Phase 2: Foundational (T016-T026)
    ↙         ↙         ↙
Phase 3:   Phase 4:    Phase 5:
User Story 1 User Story 2 User Story 3
P1 (T027-T041)  P2 (T042-T051)  P3 (T052-T061)
    ↓ (independent)
Phase 6: Styling (T062-T074)
    ↓
Phase 7: Testing (T075-T087)
    ↓
Phase 8: Deployment (T088-T106)
```

---

## Parallel Execution Examples

### Scenario A: MVP Delivery (User Story 1 Only)
**Timeline**: ~2 weeks with 2-3 developers

```
Week 1:
  Developer 1: T001-T015 (Setup & Foundational)
  Developer 2: (blocked, waiting for T015)

Week 1 Afternoon:
  Developer 1: T027-T033 (UI Components for US1)
  Developer 2: T034-T041 (API Integration for US1)

Week 2:
  Developer 1: T062-T074 (Styling)
  Developer 2: T075-T087 (Testing)

Week 2 Afternoon:
  Both: T088-T106 (Deployment & Validation)
```

### Scenario B: Full Feature (All User Stories)
**Timeline**: ~3-4 weeks with 3-4 developers

```
Week 1:
  Dev A: T001-T015 (Setup & Foundational - blocking)

Week 2:
  Dev A: Phase 3 (US1 - P1) [T027-T041]
  Dev B: Phase 4 (US2 - P2) parallel [T042-T051]
  Dev C: Phase 5 (US3 - P3) parallel [T052-T061]

Week 3:
  Dev A,B,C (parallel): Phase 6 Styling [T062-T074]

Week 3/4:
  Dev A,B,C: Phase 7 Testing [T075-T087]

Week 4:
  All: Phase 8 Deployment [T088-T106]
```

---

## Implementation Strategy

### MVP-First Approach
1. **Weeks 1-2**: Deliver User Story 1 (P1) fully functional
   - Core value: Ask question → See answer stream
   - Sufficient for demo
   - Quick win for team confidence

2. **Week 3**: Enhance with User Story 2 (P2)
   - Multi-turn conversation
   - Session persistence
   - Improved interview experience

3. **Week 3/4**: Polish with User Story 3 (P3)
   - Error handling
   - Empty states
   - Professional edge case handling

### Quality Gates
- **Phase 2 Complete**: Code is ready for component development
- **Phase 3 Complete**: MVP is testable and demo-able
- **Phase 6 Complete**: All UI styling complete and responsive
- **Phase 7 Complete**: 80% test coverage, all unit tests passing
- **Phase 8 Complete**: Production-ready, all acceptance criteria validated

---

## Notes for Implementation Team

### Critical Success Factors
1. **SSE Streaming** is non-trivial; reserve time for testing network conditions
2. **localStorage Quota** handling requires graceful degradation; test with mock quota exceeded
3. **Responsive Design** must be tested on actual devices, not just dev tools
4. **Keyboard Accessibility** is required for accessibility audits
5. **Performance** (SC-001) requires optimized bundle size and fast backend response

### Known Unknowns / Risks
- **Feature 006 Example Endpoint**: Assumes /api/v1/demo/examples endpoint exists; confirm availability early
- **CORS Configuration**: Backend must allow cross-origin requests from frontend origin; may require additional Zeabur config
- **SSE via Proxy**: If Zeabur uses proxy layer, ensure SSE works through it (some proxies have timeout issues)
- **Build Size**: If bundle >200KB, may need dynamic imports or code splitting

### Testing Challenges
- Streaming UX is hard to test with unit tests; prioritize integration and E2E tests
- Error scenarios (429, 503) may need mock backend or staging environment
- Mobile testing requires actual device or good simulator (not just dev tools resize)
- Performance testing (SC-001) needs realistic network conditions

---

## File Structure (Target)

```
src/frontend/
├── src/
│   ├── components/
│   │   ├── __tests__/
│   │   │   ├── ChatHistory.test.jsx
│   │   │   ├── ChatInput.test.jsx
│   │   │   ├── MessageBubble.test.jsx
│   │   ├── App.jsx
│   │   ├── ChatHistory.jsx
│   │   ├── ChatInput.jsx
│   │   ├── MessageBubble.jsx
│   │   ├── StreamingCursor.jsx
│   │   ├── SourceAttribution.jsx
│   │   ├── SearchStatus.jsx
│   │   ├── EmptyState.jsx
│   │   ├── ErrorAlert.jsx
│   │   ├── NewChatButton.jsx
│   ├── hooks/
│   │   ├── __tests__/
│   │   │   ├── useChat.test.js
│   │   │   ├── useLocalStorage.test.js
│   │   │   ├── useStreamingResponse.test.js
│   │   ├── useChat.js
│   │   ├── useLocalStorage.js
│   │   ├── useStreamingResponse.js
│   ├── api/
│   │   ├── __tests__/
│   │   │   ├── client.test.js
│   │   │   ├── query.test.js
│   │   ├── client.js
│   │   ├── query.js
│   │   ├── examples.js
│   ├── utils/
│   │   ├── __tests__/
│   │   │   ├── validation.test.js
│   │   ├── uuid.js
│   │   ├── validation.js
│   │   ├── storage.js
│   │   ├── errorMapping.js
│   ├── index.css
│   ├── main.jsx
│   ├── App.jsx
│   ├── __tests__/
│   │   ├── integration/
│   │   │   ├── chatFlow.test.jsx
│   ├── e2e/
│   │   ├── chat.spec.js
│   ├── public/
│   │   ├── favicon.svg
│   ├── styles/
├── .env
├── .env.production
├── vite.config.js
├── postcss.config.js
├── tailwind.config.js
├── package.json
├── README.md
├── DEVELOPMENT.md
├── DEPLOY.md
├── e2e/
│   ├── chat.spec.js
```

---

**Next Steps**: Start Phase 1 (Setup & Scaffolding) with T001. Coordinate team allocation based on Scenario A or B above.
