# CourseFlow React Chat Frontend

A modern, streaming chat interface for the CourseFlow RAG (Retrieval-Augmented Generation) system. Built with React 18, Vite, and Tailwind CSS for fast development and production builds.

## Features

- **Real-time Streaming Responses**: Watch answers appear word-by-word as the LLM generates them using Server-Sent Events (SSE)
- **Multi-turn Conversations**: Continue conversations with automatic context preservation via conversation IDs
- **Error Handling**: User-friendly error messages for rate limits, quota exhaustion, and network issues
- **Session Persistence**: Browser-based storage preserves chat history across page refreshes
- **Responsive Design**: Works seamlessly on mobile (375px) and desktop (1280px) screens
- **Empty State**: Beautiful first-load experience with clickable example questions

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start dev server (hot reload on :5173)
npm run dev

# Start backend API on :8000
# Backend must be running for chat to work
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview
```

## Architecture

### Component Hierarchy
```
App (main orchestrator)
├── Header (with NewChatButton)
├── ErrorAlert (error display)
├── ChatHistory or EmptyState (conditional)
│   ├── ChatHistory
│   │   ├── MessageBubble (repeated)
│   │   │   ├── SearchStatus (for in-progress)
│   │   │   ├── StreamingCursor (for in-progress)
│   │   │   └── SourceAttribution (for complete)
│   │   └── ChatInput
│   └── EmptyState
│       └── Example Questions (clickable)
└── ChatInput (text + send)
```

### Data Flow

1. **User submits question**
   - `ChatInput` captures text
   - `App.handleSubmitQuestion()` creates user message
   - Sends POST to `/api/v1/query/stream` with optional `conversation_id`

2. **Streaming Response**
   - Backend sends SSE events: `chunk`, `sources`, `done`, or `error`
   - `useStreamingResponse.parseSSEStream()` reads chunks
   - Component updates progressively (no full re-render per chunk)
   - Sources appear when `sources` event received
   - Conversation ID extracted from `done` event

3. **Session Persistence**
   - After response completes, `useChat` hook updates message state
   - `useEffect` in `App` saves session to localStorage
   - On page load, session restored from localStorage
   - Conversation ID reused for next question (multi-turn)

### State Management

- **App-level**: `conversationId`, `messages`, `error`, `isLoading`
- **useChat hook**: Message CRUD operations
- **useStreamingResponse hook**: SSE parsing, streaming state
- **useLocalStorage hook**: Safe localStorage read/write with quota handling

No Redux/Zustand - simple hooks are sufficient for MVP.

## API Contract

### POST /api/v1/query/stream

**Request:**
```json
{
  "question": "What is photosynthesis?",
  "conversation_id": "uuid-optional"
}
```

**Response (SSE stream):**
```
data: {"type":"chunk","content":"Photosynthesis"}
data: {"type":"chunk","content":" is..."}
data: {"type":"sources","sources":["biology/photosynthesis.md"],"retrieval_count":1}
data: {"type":"done","conversation_id":"uuid","token_count":42}
```

### GET /api/v1/demo/examples

**Response:**
```json
{
  "examples": [
    "What is photosynthesis?",
    "Explain the solar system",
    "Who was Napoleon?",
    "What is AI?"
  ]
}
```

## Configuration

### Environment Variables

**Development (.env)**
```
VITE_API_BASE_URL=http://localhost:8000
```

**Production (.env.production)**
```
VITE_API_BASE_URL=https://courseflow-backend.zeabur.app
```

Vite automatically selects the correct `.env` file based on build mode.

## Development

### Project Structure

```
src/
├── App.jsx                          # Main app component
├── index.css                        # Tailwind + global styles
├── components/                      # React components
│   ├── ChatHistory.jsx              # Scrollable message list
│   ├── ChatInput.jsx                # Text input + send
│   ├── MessageBubble.jsx            # Individual message
│   ├── StreamingCursor.jsx          # Blinking cursor
│   ├── SearchStatus.jsx             # "Searching..." indicator
│   ├── SourceAttribution.jsx        # Source links
│   ├── NewChatButton.jsx            # Reset conversation
│   ├── EmptyState.jsx               # Initial screen
│   └── ErrorAlert.jsx               # Error display
├── hooks/                           # Custom React hooks
│   ├── useChat.js                   # Message state management
│   ├── useStreamingResponse.js      # SSE parsing
│   └── useLocalStorage.js           # Safe localStorage
├── api/                             # API client
│   ├── client.js                    # Fetch wrapper
│   └── query.js                     # Query endpoints
└── utils/                           # Utilities
    ├── uuid.js                      # UUID v4 generation
    ├── validation.js                # Input validation
    ├── storage.js                   # localStorage helpers
    └── errorMapping.js              # Error message mapping
```

### Code Style

- **Language**: JavaScript (not TypeScript for MVP speed)
- **React**: Functional components with hooks
- **State**: Only useState/useRef (no Redux)
- **Styling**: Tailwind CSS utility classes
- **HTTP**: Native Fetch API with async/await

### Build Tools

- **Bundler**: Vite v7 (103ms startup, instant HMR)
- **CSS**: Tailwind CSS v4 with @tailwindcss/postcss
- **Target**: ES2020 (modern browsers only)
- **Output**: ~64 kB gzipped (under 200 KB limit)

## Testing

Test files are stubbed but not implemented (MVP phase):

```bash
# Run tests (when ready)
npm run test

# Run with coverage
npm run test:cov
```

Existing test stubs:
- `src/utils/__tests__/validation.test.js`
- `src/hooks/__tests__/useLocalStorage.test.js`
- `src/api/__tests__/client.test.js`

## Deployment

See [DEPLOY.md](./DEPLOY.md) for complete deployment guide to Zeabur.

Quick summary:
1. Build: `npm run build`
2. Deploy: Push to GitHub, Zeabur auto-deploys via webhook
3. Verify: Check `/api/v1/demo/examples` response
4. Validate: Run all 9 success criteria from DEPLOY.md

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Tested on:
- Desktop: macOS 12+, Windows 10+
- Mobile: iOS 14+, Android 8+

## Performance Targets

- **First word**: <1500ms (typical: 800-1200ms with latency)
- **Build size**: <200 KB gzipped (actual: ~64 KB)
- **Dev startup**: <150ms (actual: 103ms)
- **Full response**: <60 seconds (typical: 15-30 seconds)

## Known Limitations

- **No Markdown rendering**: Plain text only (can be added in Phase 6)
- **No dark mode**: Light theme only (can be toggled in Tailwind config)
- **No message editing**: Can't modify sent messages (UI feature, not API)
- **No TypeScript**: JavaScript only for development speed
- **localStorage only**: No cross-device sync (frontend-only storage)

## Troubleshooting

### "CORS policy blocked request"
- Verify backend is running and accessible
- Check `VITE_API_BASE_URL` in `.env` matches backend location
- Ensure backend has CORS headers enabled

### "Chat input not responsive"
- Check if `isLoading` is stuck true
- Open DevTools Console for errors
- Verify backend responded (check Network tab)

### "Session not persisting"
- Browser localStorage might be disabled
- Private/Incognito mode disables persistent storage
- Check QuotaExceededError in console (storage full)

### "Examples not loading"
- Backend `/api/v1/demo/examples` might not exist
- Falls back to hardcoded defaults if API fails
- Check Network tab for endpoint response

## Contributing

1. Ensure `npm run build` passes before committing
2. Keep components under 50 lines where possible
3. Use meaningful variable names (no single letters except loops)
4. Comment only non-obvious logic
5. Test at 375px and 1280px breakpoints

## License

MIT - See LICENSE file

## Support

- Issues: Check [DEPLOY.md](./DEPLOY.md) troubleshooting section
- Backend docs: `../src/courseflow/README.md`
- API docs: `http://localhost:8000/docs` (when running backend)
