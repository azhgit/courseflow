import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header.jsx';
import { ChatHistory } from './components/ChatHistory.jsx';
import { FixedInput } from './components/FixedInput.jsx';
import { EmptyState } from './components/EmptyState.jsx';
import { ErrorAlert } from './components/ErrorAlert.jsx';
import { useChat } from './hooks/useChat.js';
import { useStreamingResponse } from './hooks/useStreamingResponse.js';
import { postQuery, getExampleQuestions } from './api/query.js';
import { loadSession, saveSession, clearSession } from './utils/storage.js';
import { generateUUIDv4 } from './utils/uuid.js';
import { mapSSEErrorToErrorState } from './utils/errorMapping.js';
import './index.css';

function App() {
  const {
    conversationId,
    setConversationId,
    messages,
    setMessages,
    isLoading,
    setIsLoading,
    error,
    setError,
    addUserMessage,
    clearChat: resetChatState,
  } = useChat();

  const { parseSSEStream } = useStreamingResponse();
  const abortControllerRef = useRef(null);
  const [examples, setExamples] = useState([]);

  useEffect(() => {
    const session = loadSession();
    if (session) {
      setConversationId(session.conversation_id);
      setMessages(session.messages);
    }

    const loadExamples = async () => {
      const loaded = await getExampleQuestions();
      if (loaded) {
        setExamples(loaded);
      }
    };
    loadExamples();
  }, [setConversationId, setMessages]);

  useEffect(() => {
    if (messages.length > 0 && conversationId) {
      const session = {
        conversation_id: conversationId,
        messages,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      saveSession(session);
    }
  }, [messages, conversationId]);

  useEffect(() => {
    if (!error) return undefined;

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setError(null);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [error, setError]);

  const handleNewChat = () => {
    resetChatState();
    clearSession();
  };

  const handleExampleClick = (question) => {
    handleSubmitQuestion(question);
  };

  const handleSubmitQuestion = async (question) => {
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);
    addUserMessage(question);

    const assistantMessageId = generateUUIDv4();
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        status: 'in-progress',
        timestamp: new Date().toISOString(),
      },
    ]);

    let assistantContent = '';
    let assistantSources = [];

    try {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const response = await postQuery(question, conversationId);

      await parseSSEStream(
        response,
        (chunk) => {
          assistantContent += chunk;
          setMessages((prev) => {
            const updated = [...prev];
            const assistantMsg = updated.find((m) => m.id === assistantMessageId);
            if (assistantMsg) {
              assistantMsg.content = assistantContent;
            }
            return updated;
          });
        },
        (sources) => {
          assistantSources = (sources || []).map((source) => {
            if (typeof source === 'string') {
              return { name: source };
            }
            if (source && typeof source === 'object') {
              if (typeof source.name === 'string' && source.name.trim()) {
                return { name: source.name };
              }
              if (typeof source.source === 'string' && source.source.trim()) {
                return { name: source.source };
              }
            }
            return { name: String(source) };
          });
        },
        (errorEvent) => {
          const errorState = mapSSEErrorToErrorState(errorEvent.error, errorEvent.message);
          setError(errorState);
          setIsLoading(false);
        },
        () => {
          setMessages((prev) => {
            const updated = [...prev];
            const assistantMsg = updated.find((m) => m.id === assistantMessageId);
            if (assistantMsg) {
              assistantMsg.status = 'complete';
              assistantMsg.sources = assistantSources;
            }
            return updated;
          });
          setIsLoading(false);
        },
        (receivedConversationId) => {
          if (!conversationId || conversationId !== receivedConversationId) {
            setConversationId(receivedConversationId);
          }
        }
      );
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError({
          type: 'network_error',
          message: 'Connection lost. Please check your network and try again.',
        });
      }
      setIsLoading(false);
    }
  };

  const showEmptyState = messages.length === 0 && !isLoading;
  const showHeader = messages.length > 0;

  // Calculate input placeholder based on current state
  const inputPlaceholder = showEmptyState
    ? 'Ask a question about your course content…'
    : 'Ask a follow-up question…';

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* ── Header: only show on chat page (has messages) ── */}
      {showHeader && <Header onNewChat={handleNewChat} onReturnHome={handleNewChat} />}

      {/* ── Main content area ── */}
      <main className={`relative flex flex-1 flex-col ${showHeader ? 'pt-14' : ''}`}>
        {/* ── Error alert (if present) ── */}
        {error && (
          <ErrorAlert
            error={error}
            onDismiss={() => setError(null)}
            onRetry={() => {
              setError(null);
              if (messages.length > 0) {
                const lastMessage = messages[messages.length - 1];
                if (lastMessage.role === 'user') {
                  handleSubmitQuestion(lastMessage.content);
                }
              }
            }}
          />
        )}

        {/* ── Empty state or chat history ── */}
        <div className="flex-1 overflow-hidden">
          {showEmptyState ? (
            <EmptyState
              examples={examples}
              onExampleClick={handleExampleClick}
            />
          ) : (
            <ChatHistory messages={messages} isLoading={isLoading} />
          )}
        </div>
      </main>

      {/* ── Fixed input at bottom (for both landing and chat) ── */}
      <FixedInput
        onSubmit={handleSubmitQuestion}
        isDisabled={isLoading}
        placeholder={inputPlaceholder}
      />
    </div>
  );
}

export default App;
