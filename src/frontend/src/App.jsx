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

  useEffect(() => {
    const session = loadSession();
    if (session) {
      setConversationId(session.conversation_id);
      setMessages(session.messages);
    }

    const loadExamples = async () => {
      const loaded = await getExampleQuestions();
      if (loaded) setExamples(loaded);
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
          assistantSources = (sources || []).map((source) => {
            if (typeof source === 'string') return { name: source };
            if (source && typeof source === 'object') {
              if (typeof source.name === 'string' && source.name.trim()) return { name: source.name };
              if (typeof source.source === 'string' && source.source.trim()) return { name: source.source };
            }
            return { name: String(source) };
          });
        },
        (errorEvent) => {
          setError(mapSSEErrorToErrorState(errorEvent.error, errorEvent.message));
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
              // find the most recent user message to retry
              for (let i = messages.length - 1; i >= 0; i--) {
                const m = messages[i];
                if (m?.role === 'user' && m?.content && m.content.trim()) {
                  handleSubmitQuestion(m.content);
                  return;
                }
              }
              // fallback: do nothing if no user message found
            }}
          />
        )}

        <div className="flex-1 overflow-y-auto">
          {showEmptyState ? (
            <EmptyState
              examples={examples}
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