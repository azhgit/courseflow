import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header.jsx';
import { ChatHistory } from './components/ChatHistory.jsx';
import { ChatInput } from './components/ChatInput.jsx';
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
  const [isExamplesLoading, setIsExamplesLoading] = useState(true);

  useEffect(() => {
    const session = loadSession();
    if (session) {
      setConversationId(session.conversation_id);
      setMessages(session.messages);
    }

    const loadExamples = async () => {
      setIsExamplesLoading(true);
      const loaded = await getExampleQuestions();
      if (loaded) setExamples(loaded);
      setIsExamplesLoading(false);
    };
    loadExamples();
  }, [setConversationId, setMessages]);

  useEffect(() => {
    if (messages.length > 0 && conversationId) {
      saveSession({
        conversation_id: conversationId,
        messages,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }
  }, [messages, conversationId]);

  useEffect(() => {
    if (!error) return undefined;
    const onKeyDown = (e) => { if (e.key === 'Escape') setError(null); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [error, setError]);

  const handleNewChat = () => {
    resetChatState();
    clearSession();
  };

  const handleExampleClick = (question) => handleSubmitQuestion(question);

  const handleSubmitQuestion = async (question, options = {}) => {
    if (!question.trim()) return;

    const { skipUserMessage = false, reuseAssistantId = null } = options;

    setIsLoading(true);
    setError(null);

    // Only add user message if not skipping (i.e., not a retry)
    if (!skipUserMessage) {
      addUserMessage(question);
    }

    // Reuse existing assistant message ID or create a new one
    const assistantMessageId = reuseAssistantId || generateUUIDv4();

    if (reuseAssistantId) {
      // Reset the existing assistant message for retry
      setMessages((prev) =>
        prev.map((m) =>
          m.id === reuseAssistantId
            ? { ...m, content: '', status: 'in-progress', timestamp: new Date().toISOString() }
            : m
        )
      );
    } else {
      // Add new assistant message
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
    }

    let assistantContent = '';
    let assistantSources = [];

    try {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();

      const response = await postQuery(question, conversationId);

      await parseSSEStream(
        response,
        (chunk) => {
          assistantContent += chunk;
          setMessages((prev) => {
            const updated = [...prev];
            const msg = updated.find((m) => m.id === assistantMessageId);
            if (msg) msg.content = assistantContent;
            return updated;
          });
        },
        (sources) => {
          const normalizeSource = (source) => {
            let path = '';
            let name = '';

            if (typeof source === 'string') {
              path = source.trim();
            } else if (source && typeof source === 'object') {
              if (typeof source.path === 'string' && source.path.trim()) {
                path = source.path.trim();
              } else if (typeof source.source === 'string' && source.source.trim()) {
                path = source.source.trim();
              }

              if (typeof source.name === 'string' && source.name.trim()) {
                name = source.name.trim();
              }
            }

            const basename = (path || name).split('/').filter(Boolean).pop() || (path || name || String(source));
            return {
              name: basename,
              path: path || basename,
            };
          };

          const normalized = (sources || []).map(normalizeSource);

          // If both "docs/.../file.md" and "file.md" exist, keep only the full-path one.
          const hasFullPathByBase = new Set(
            normalized
              .filter((item) => typeof item.path === 'string' && item.path.includes('/'))
              .map((item) => item.name.toLowerCase())
          );

          const filtered = normalized.filter((item) => {
            const isBareName = typeof item.path === 'string' && !item.path.includes('/');
            return !(isBareName && hasFullPathByBase.has(item.name.toLowerCase()));
          });

          const seenPaths = new Set();
          assistantSources = filtered.filter((item) => {
            const key = (item.path || item.name).toLowerCase();
            if (seenPaths.has(key)) return false;
            seenPaths.add(key);
            return true;
          });
        },
        (errorEvent) => {
          setError(
            mapSSEErrorToErrorState(
              errorEvent.error,
              errorEvent.message,
              errorEvent.error_source
            )
          );
          setIsLoading(false);
        },
        () => {
          setMessages((prev) => {
            const updated = [...prev];
            const msg = updated.find((m) => m.id === assistantMessageId);
            if (msg) {
              msg.status = 'complete';
              msg.sources = assistantSources;
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

  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-[#F8FAFC] to-[#F1F5F9]">

      {showHeader && (
        <Header onNewChat={handleNewChat} onReturnHome={handleNewChat} />
      )}

      <main className="flex flex-1 flex-col overflow-hidden">

        {error && (
          <ErrorAlert
            error={error}
            onDismiss={() => setError(null)}
            onRetry={() => {
              setError(null);
              // Find the last in-progress assistant message and the user question before it
              let userQuestion = null;
              let assistantId = null;
              for (let i = messages.length - 1; i >= 0; i--) {
                const m = messages[i];
                if (!assistantId && m?.role === 'assistant' && m?.status === 'in-progress') {
                  assistantId = m.id;
                }
                if (m?.role === 'user' && m?.content && m.content.trim()) {
                  userQuestion = m.content;
                  break;
                }
              }
              if (userQuestion) {
                handleSubmitQuestion(userQuestion, {
                  skipUserMessage: true,
                  reuseAssistantId: assistantId,
                });
              }
            }}
          />
        )}

        <div className="flex-1 overflow-y-auto">
          {showEmptyState ? (
            <EmptyState
              examples={examples}
              isExamplesLoading={isExamplesLoading}
              onExampleClick={handleExampleClick}
              onSubmit={handleSubmitQuestion}
              isDisabled={isLoading}
            />
          ) : (
            <ChatHistory messages={messages} isLoading={isLoading} />
          )}
        </div>

        {!showEmptyState && (
          <ChatInput onSubmit={handleSubmitQuestion} isDisabled={isLoading} />
        )}
      </main>
    </div>
  );
}

export default App;
