import { useState, useEffect, useRef } from 'react';
import { ChatHistory } from './components/ChatHistory.jsx';
import { ChatInput } from './components/ChatInput.jsx';
import { NewChatButton } from './components/NewChatButton.jsx';
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

  // Restore session from localStorage on mount
  useEffect(() => {
    const session = loadSession();
    if (session) {
      setConversationId(session.conversation_id);
      setMessages(session.messages);
    }

    // Load example questions on mount
    const loadExamples = async () => {
      const loaded = await getExampleQuestions();
      if (loaded) {
        setExamples(loaded);
      }
    };
    loadExamples();
  }, []);

  // Save session to localStorage whenever it changes
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

    // Add user message to history
    addUserMessage(question);

    // Use existing conversation id only; backend creates one for first turn
    const currentConversationId = conversationId;

    // Create placeholder for assistant message
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
      // Cancel any previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      // Post question to backend
      const response = await postQuery(question, currentConversationId);

      // Parse SSE stream
      await parseSSEStream(
        response,
        (chunk) => {
          // Update assistant message with chunk
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
          // Backend returns list[str] for sources; normalize for UI
          assistantSources = (sources || []).map((source) =>
            typeof source === 'string' ? { name: source } : source
          );
        },
        (errorEvent) => {
          // Handle SSE error
          const errorState = mapSSEErrorToErrorState(errorEvent.error, errorEvent.message);
          setError(errorState);
          setIsLoading(false);
        },
        () => {
          // On done: finalize message
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
        console.error('Error submitting question:', err);
        setError({
          type: 'network_error',
          message: 'Connection lost. Please check your network and try again.',
        });
      }
      setIsLoading(false);
    }
  };

  // Show empty state if no messages
  const showEmptyState = messages.length === 0 && !isLoading;

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-sm">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">CourseFlow Chat</h1>
          <NewChatButton onNewChat={handleNewChat} />
        </div>
      </header>

      {/* Error Message */}
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

      {/* Empty State or Chat History */}
      {showEmptyState ? (
        <EmptyState examples={examples} onExampleClick={handleExampleClick} />
      ) : (
        <ChatHistory messages={messages} isLoading={isLoading} />
      )}

      {/* Chat Input */}
      <ChatInput
        onSubmit={handleSubmitQuestion}
        isDisabled={isLoading}
      />
    </div>
  );
}

export default App;
