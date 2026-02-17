# Data Model: React Chat Interface MVP

**Feature**: 007-react-frontend-mvp  
**Created**: 2026-02-17  
**Scope**: Frontend client-side entities, localStorage schema, and API contracts

---

## Core Entities

### 1. ChatSession

**Purpose**: Container for entire chat conversation within a single browser session

**Attributes**:
```typescript
interface ChatSession {
  // Unique identifier for this conversation across turns
  conversation_id: string; // UUID v4
  
  // All messages in this conversation, in chronological order
  messages: Message[];
  
  // Metadata
  created_at: string; // ISO 8601 timestamp
  updated_at: string; // ISO 8601 timestamp, updated on every message add
}
```

**Validation Rules**:
- `conversation_id`: Must be valid UUID v4 format
- `messages`: Array must not be empty when session is active
- `created_at`, `updated_at`: Must be valid ISO 8601 strings
- `updated_at` must be >= `created_at`

**Lifecycle**:
- Created: When page loads with no prior session OR user clicks "New Chat"
- Updated: After each new message or user action
- Destroyed: On "New Chat" or user-triggered clear

**Storage Location**: Browser localStorage (key: `courseflow_session`)

---

### 2. Message

**Purpose**: Individual chat message (user or assistant response)

**Attributes**:
```typescript
interface Message {
  // Unique ID within session
  id: string; // UUID v4
  
  // Role in conversation
  role: 'user' | 'assistant';
  
  // Message text content (plain text only, no markdown)
  content: string;
  
  // Source attribution (only for assistant messages)
  sources?: Source[];
  
  // Lifecycle status
  status: 'in-progress' | 'complete';
  
  // When this message was created
  timestamp: string; // ISO 8601 timestamp
}
```

**Validation Rules**:
- `id`: Must be valid UUID v4
- `role`: Must be one of 'user' or 'assistant'
- `content`: Must be non-empty string (max 10,000 chars for safety)
- `sources`: Only present for assistant messages; undefined for user
- `status`: 
  - User messages: Always 'complete'
  - Assistant messages: 'in-progress' while streaming, 'complete' when done
- `timestamp`: Must be valid ISO 8601

**State Transitions**:
- User message: created as 'complete', never changes
- Assistant message: created as 'in-progress', transitions to 'complete' on stream end
- Content field: Grows as chunks arrive for in-progress messages

**Examples**:

User message (complete immediately):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "user",
  "content": "What is photosynthesis?",
  "timestamp": "2026-02-17T10:30:00Z",
  "status": "complete"
}
```

Assistant message (in-progress):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "role": "assistant",
  "content": "Photosynthesis is the process by which plants convert light energy into chemical energy. It occurs primarily in the chloroplasts...",
  "sources": [
    { "name": "Biology: Photosynthesis Overview", "url": null },
    { "name": "Plant Physiology Chapter 3", "url": null }
  ],
  "timestamp": "2026-02-17T10:30:02Z",
  "status": "complete"
}
```

---

### 3. Source

**Purpose**: Attribution for retrieved documents in assistant response

**Attributes**:
```typescript
interface Source {
  // Display name of source document
  name: string;
  
  // Optional URL to source (not used in MVP, reserved for future)
  url?: string;
}
```

**Validation Rules**:
- `name`: Must be non-empty string (max 200 chars)
- `url`: If present, must be valid URL format

**Examples**:
```json
{ "name": "Programming: Python Async Patterns" }
{ "name": "History: World War II Events" }
{ "name": "Biology: Cell Structure and Function" }
```

**Presentation**:
- Shown below completed assistant message
- Format: "Sources: [Doc 1], [Doc 2], ..."
- Links not clickable in MVP (docs are local, not web-accessible)

---

### 4. ErrorState

**Purpose**: Represent error conditions and display appropriate user messages

**Attributes**:
```typescript
interface ErrorState {
  // Type of error occurred
  type: 'ip_limit' | 'daily_quota' | 'no_documents' | 'network_error';
  
  // User-facing error message
  message: string;
  
  // Retry guidance (seconds to wait if applicable)
  retry_after?: number;
}
```

**Validation Rules**:
- `type`: Must be one of the four defined types
- `message`: Must be exact string defined for this type
- `retry_after`: Only present for rate-limit errors

**Mapping** (from HTTP response or stream error):

| Type | HTTP Status | User Message |
|------|------------|--------------|
| `ip_limit` | 429 | "Demo limit reached. Try again in 1 hour." |
| `daily_quota` | 429 | "Daily demo limit reached. Resets at midnight." |
| `no_documents` | Event `error: no_relevant_documents` | "No content found for this query. Try rephrasing your question." |
| `network_error` | Any network failure | "Connection lost. Please check your network and try again." |

**Examples**:
```json
{
  "type": "ip_limit",
  "message": "Demo limit reached. Try again in 1 hour.",
  "retry_after": 3600
}
```

```json
{
  "type": "no_documents",
  "message": "No content found for this query. Try rephrasing your question."
}
```

---

## localStorage Schema

### Key: `courseflow_session`

**Value**: JSON-serialized ChatSession object

**Example**:
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "role": "user",
      "content": "What is photosynthesis?",
      "timestamp": "2026-02-17T10:30:00Z",
      "status": "complete"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "role": "assistant",
      "content": "Photosynthesis is a process...",
      "sources": [
        { "name": "Biology Basics" }
      ],
      "timestamp": "2026-02-17T10:30:02Z",
      "status": "complete"
    }
  ],
  "created_at": "2026-02-17T10:29:55Z",
  "updated_at": "2026-02-17T10:30:02Z"
}
```

**Serialization Notes**:
- Use `JSON.stringify()` for writing
- Use `JSON.parse()` for reading
- Validate schema on read (malformed data → discard, show empty state)

**Size Management**:
- Typical session: 2-5KB (5-10 messages)
- Storage limit: 5-10MB (browser dependent)
- Safe capacity: ~1000 messages per session
- If quota exceeded: Keep in-memory only, don't persist

---

## API Request/Response Format

### Request: POST /api/v1/query

**Body**:
```json
{
  "question": string,
  "conversation_id": string | null
}
```

**Headers**:
```
Content-Type: application/json
```

**Notes**:
- First message: `conversation_id: null` or omitted
- Backend returns `conversation_id` in first event
- Subsequent messages: Include `conversation_id` for continuity

---

### Response: Server-Sent Events Stream

**Format**: Text stream with newline-delimited JSON objects

**Example Stream**:
```
data: {"type":"start","conversation_id":"550e8400-...","timestamp":"2026-02-17T10:30:02Z"}
data: {"type":"chunk","content":"Photosynthesis "}
data: {"type":"chunk","content":"is the process "}
data: {"type":"chunk","content":"by which plants..."}
data: {"type":"sources","sources":[{"name":"Biology: Photosynthesis Overview"}]}
data: {"type":"done","timestamp":"2026-02-17T10:30:05Z"}
```

**Event Types**:

#### `start` Event (first event)
```json
{
  "type": "start",
  "conversation_id": "UUID",
  "timestamp": "2026-02-17T10:30:02Z"
}
```

#### `chunk` Event (one or more)
```json
{
  "type": "chunk",
  "content": "text content of this chunk..."
}
```

#### `sources` Event (optional, when available)
```json
{
  "type": "sources",
  "sources": [
    { "name": "Document Name 1" },
    { "name": "Document Name 2" }
  ]
}
```

#### `error` Event (if error during processing)
```json
{
  "type": "error",
  "error_type": "no_relevant_documents",
  "message": "No content found for this query. Try rephrasing your question."
}
```

#### `done` Event (last event)
```json
{
  "type": "done",
  "timestamp": "2026-02-17T10:30:05Z"
}
```

---

## HTTP Error Status Codes

| Status | Body | Meaning | User Message |
|--------|------|---------|--------------|
| 200 | SSE stream | Success | (Stream events shown progressively) |
| 429 | `{"error": "ip_rate_limit_exceeded"}` | Hourly limit hit | "Demo limit reached. Try again in 1 hour." |
| 429 | `{"error": "daily_quota_exhausted"}` | Daily limit hit | "Daily demo limit reached. Resets at midnight." |
| 503 | `{"error": "service_unavailable"}` | Backend error | "Service unavailable. Try again later." |
| 5xx | Any | Server error | "Server error. Please try again." |

---

## State Transitions Diagram

### ChatSession Lifecycle
```
                    Page Load
                        ↓
           ┌────────────────────────┐
           │ Check localStorage     │
           └────────────────────────┘
                ↙            ↘
        Found Valid         Not Found
             ↓                   ↓
        ┌─────────┐         ┌──────────┐
        │Restore  │         │Empty     │
        │Session  │         │State     │
        └─────────┘         └──────────┘
             ↓                   ↓
        ┌───────────────────────────┐
        │  User Sends Message       │
        └───────────────────────────┘
             ↓
        ┌───────────────────────────┐
        │ SSE Stream Completes      │
        │ Save to localStorage      │
        └───────────────────────────┘
             ↓
        ┌───────────────────────────┐
        │ User Sends Follow-up      │
        │ (Reuse conversation_id)   │
        └───────────────────────────┘
             ↓
             ... (cycle continues)
             ↓
        ┌───────────────────────────┐
        │ "New Chat" Clicked        │
        │ Clear localStorage +      │
        │ Clear memory              │
        └───────────────────────────┘
             ↓
        ┌──────────────┐
        │ Empty State  │
        └──────────────┘
```

### Message Status Lifecycle
```
User Message:
    Created → complete (no transition)

Assistant Message:
    Created (in-progress)
         ↓
    Chunks arrive (append to content)
         ↓
    'done' event received
         ↓
    transition to complete + save to localStorage
```

---

## Serialization & Persistence

### Writing to localStorage
```javascript
const saveSession = (session) => {
  try {
    const json = JSON.stringify(session);
    localStorage.setItem('courseflow_session', json);
  } catch (e) {
    if (e.name === 'QuotaExceededError') {
      console.warn('localStorage quota exceeded, session not persisted');
      // Continue with in-memory only
    } else {
      console.error('localStorage error:', e);
    }
  }
};
```

### Reading from localStorage
```javascript
const loadSession = () => {
  try {
    const json = localStorage.getItem('courseflow_session');
    if (!json) return null;
    
    const session = JSON.parse(json);
    
    // Validate schema
    if (!session.conversation_id || !Array.isArray(session.messages)) {
      console.warn('Invalid session schema, discarding');
      return null;
    }
    
    return session;
  } catch (e) {
    console.error('Failed to load session:', e);
    return null;
  }
};
```

---

## Validation Functions

### Validate ChatSession
```javascript
const isValidSession = (obj) => {
  return (
    typeof obj === 'object' &&
    typeof obj.conversation_id === 'string' &&
    Array.isArray(obj.messages) &&
    typeof obj.created_at === 'string' &&
    typeof obj.updated_at === 'string' &&
    isValidUUID(obj.conversation_id) &&
    obj.messages.every(isValidMessage) &&
    isValidISO8601(obj.created_at) &&
    isValidISO8601(obj.updated_at)
  );
};
```

### Validate Message
```javascript
const isValidMessage = (obj) => {
  return (
    typeof obj === 'object' &&
    isValidUUID(obj.id) &&
    ['user', 'assistant'].includes(obj.role) &&
    typeof obj.content === 'string' &&
    obj.content.length > 0 &&
    obj.content.length <= 10000 &&
    ['in-progress', 'complete'].includes(obj.status) &&
    isValidISO8601(obj.timestamp) &&
    (!obj.sources || Array.isArray(obj.sources) && obj.sources.every(isValidSource))
  );
};
```

---

## Next Steps

1. ✅ Data model defined with validation rules
2. 🟡 API contracts documented (in contracts/query-streaming.md)
3. 🔲 Component state interface design
4. 🔲 Hook signatures (useChat, useLocalStorage, useStreamingResponse)
