# Feature Specification: React Chat Interface MVP for CourseFlow Demo

**Feature Branch**: `007-react-frontend-mvp`  
**Created**: 2026-02-17  
**Status**: Draft  
**Input**: User description: "React Chat Interface MVP for CourseFlow Demo"

## Clarifications

### Session 2026-02-17

- Q: How should the frontend connect to the backend API endpoint? → A: Environment variable for backend URL with local dev fallback
- Q: What happens to chat history on browser page refresh? → A: Store in browser localStorage to survive refresh
- Q: What should the four example questions contain? → A: Questions from precached demo set

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask and receive streamed answers (Priority: P1)

A developer presenting CourseFlow can enter a question in a chat interface and see the assistant answer begin quickly, then continue progressively until completion.

**Why this priority**: This is the core demo value; without a working ask/answer loop, interviewers cannot evaluate the RAG experience.

**Independent Test**: Can be fully tested by opening the public chat page, submitting one question, and verifying progressive answer rendering from start to completion.

**Acceptance Scenarios**:

1. **Given** the chat page is open and input has text, **When** the user submits via Enter or Send, **Then** the question is added to history and processing starts.
2. **Given** processing has started and no answer text has arrived yet, **When** the system is retrieving context, **Then** a visible "Searching knowledge base" status is shown.
3. **Given** answer chunks are received, **When** each chunk arrives, **Then** the in-progress assistant message updates progressively instead of waiting for full completion.
4. **Given** streaming is in progress, **When** the answer is not complete, **Then** a visible typing cursor appears at the end of the assistant message.
5. **Given** the final completion event is received, **When** rendering finalizes, **Then** the typing cursor disappears and source document names are shown under that answer.

---

### User Story 2 - Continue multi-turn conversation (Priority: P2)

A presenter can ask follow-up questions in the same session so interviewers can observe conversation continuity.

**Why this priority**: Multi-turn continuity demonstrates product coherence and improves interview demo quality.

**Independent Test**: Can be tested by asking two related questions and verifying the second response behaves as a follow-up in the same session context.

**Acceptance Scenarios**:

1. **Given** a conversation is already active, **When** the user sends another question, **Then** the system reuses the same conversation identifier for continuity.
2. **Given** the user clicks New Chat, **When** reset is confirmed, **Then** prior history is cleared and a fresh conversation identifier is used for the next question.
3. **Given** the page is refreshed during an active conversation, **When** the page reloads, **Then** the message history and conversation identifier are restored from browser storage.

---

### User Story 3 - Handle demo-safe empty and error states (Priority: P3)

An interviewer can understand what is happening even when no results are found or quota/network limits occur.

**Why this priority**: Reliable and understandable failure behavior prevents demo disruption and preserves confidence in the system.

**Independent Test**: Can be tested by triggering each error condition and verifying the expected user-facing message.

**Acceptance Scenarios**:

1. **Given** no query has been sent yet, **When** the page loads, **Then** a centered empty state with brand mark and four selectable example questions from the precached demo set is shown.
2. **Given** a rate-limit response is returned, **When** the request fails with hourly limit status, **Then** the user sees "Demo limit reached. Try again in 1 hour.".
3. **Given** a daily budget exhaustion response is returned, **When** the request fails with daily-limit status, **Then** the user sees "Daily demo limit reached. Resets at midnight.".
4. **Given** the answer stream reports no relevant documents, **When** the stream ends with that error, **Then** the user sees "No content found for this query. Try rephrasing your question.".
5. **Given** a network failure occurs before completion, **When** connectivity fails, **Then** the user sees a clear retry-oriented network error message.

---

### Edge Cases

- User submits an empty or whitespace-only question.
- User submits rapidly multiple times before prior stream completes.
- First chunk is delayed beyond expected latency while connection remains open.
- Stream closes unexpectedly after partial content is shown.
- Source list is empty for an otherwise completed response.
- Mobile viewport causes long responses and sources to overflow.
- User refreshes browser during active streaming (partial response recovery behavior).
- localStorage quota exceeded (graceful degradation to in-memory only).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a public web chat page accessible without local setup.
- **FR-002**: System MUST allow question submission by both Enter key and Send button.
- **FR-003**: System MUST append each user question and assistant response to a scrollable chronological history in the current session.
- **FR-004**: System MUST render assistant responses progressively as streamed chunks arrive.
- **FR-005**: System MUST display a retrieval status indicator between submission and first answer chunk.
- **FR-006**: System MUST display a visible streaming cursor while an assistant response is still in progress.
- **FR-007**: System MUST show source document names beneath each completed assistant response.
- **FR-008**: System MUST preserve one conversation identifier across turns until the user starts a new chat.
- **FR-009**: System MUST provide a New Chat action that clears message history and resets conversation continuity for the next turn.
- **FR-010**: System MUST present user-friendly, condition-specific messages for hourly quota exceeded, daily quota exhausted, no relevant documents, and network failure.
- **FR-011**: System MUST provide an initial empty state with a centered brand visual and four example questions from the backend's precached demo question set that can populate the input when selected.
- **FR-012**: System MUST remain usable on both small mobile and desktop viewport widths defined in Success Criteria.
- **FR-013**: System MUST keep message content plain text for this MVP.
- **FR-014**: System MUST read backend API base URL from an environment variable, with localhost fallback for local development.
- **FR-015**: System MUST persist message history and conversation identifier to browser localStorage to survive page refresh.
- **FR-016**: System MUST restore persisted conversation state on page load if available.

### Key Entities *(include if feature involves data)*

- **Chat Session**: A single active conversation context containing a conversation identifier and ordered messages; persisted to browser localStorage.
- **Message**: One chat item with role (user or assistant), text content, lifecycle state (in-progress or complete), and optional sources.
- **Source Attribution**: A list of source document display names associated with one completed assistant response.
- **Error State**: A classified failure condition mapped to a specific user-facing message.
- **Example Prompt**: A pre-defined starter question from the precached demo set, shown in the empty state and insertable into the input field.

## Assumptions

- The backend endpoint is reachable from the public frontend origin and is configured to allow cross-origin browser access.
- Browser localStorage is sufficient for demo session persistence (no cross-device sync required).
- English-language user-facing messaging is acceptable for the MVP demo.
- Backend API URL is provided via build-time or runtime environment variable (e.g., `VITE_API_BASE_URL`), defaulting to `http://localhost:8000` for local development.
- The backend demo cache (feature 006) provides at least four precached questions that can be used as example prompts.

## Dependencies

- Availability of a stable public deployment target for the frontend.
- Availability of the existing CourseFlow query backend with streaming and error signaling.
- Backend API URL must be configurable per deployment environment (development vs production).
- Browser localStorage API availability (standard in all modern browsers).
- Backend demo cache feature (006) with precached question set must be available to populate example prompts.

## Out of Scope

- User authentication and identity management.
- Document upload and content management interfaces.
- Rich text or markdown rendering in messages.
- Dark mode, offline mode, or installable app behavior.
- Message edit, copy, or delete capabilities.
- Cross-device or cross-browser session sync.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For at least 95% of successful queries under normal demo conditions, users see the first assistant word within 1.5 seconds of submission.
- **SC-002**: During streaming responses, visible answer updates occur continuously with no perceived multi-second batch jumps for users.
- **SC-003**: For 100% of completed assistant responses, source attribution appears directly beneath the associated answer.
- **SC-004**: New Chat fully resets visible history and conversation continuity in 100% of validation runs.
- **SC-005**: The defined user-facing messages for hourly limit, daily limit, and no-content conditions are shown exactly as specified when those conditions occur.
- **SC-006**: Interface remains fully usable at 375px and 1280px viewport widths, including input, history, and source readability.
- **SC-007**: Users can complete one end-to-end question flow from open page to completed answer without setup steps in under 60 seconds.
- **SC-008**: After browser refresh, 100% of completed message history is restored and displayed correctly.
- **SC-009**: All four example questions in the empty state result in instant cache hits with no API quota consumption.

### Performance & UX Targets (if applicable)

- **Page Load**: Primary chat interface is ready for first input within 3 seconds on a standard broadband connection.
- **API Performance**: User-perceived first answer token meets SC-001 and stream remains visibly progressive.
- **Accessibility**: Keyboard-only users can submit questions and start a new chat without pointer interaction.
- **Responsive Design**: Core chat interactions are fully functional from 375px to 1280px widths.
