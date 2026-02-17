import { useState, useEffect, useRef } from 'react';
import { ChatHistory } from './components/ChatHistory.jsx';
import { ChatInput } from './components/ChatInput.jsx';
import { NewChatButton } from './components/NewChatButton.jsx';
import { EmptyState } from './components/EmptyState.jsx';
import { ErrorAlert } from './components/ErrorAlert.jsx';
import { useChat } from './hooks/useChat.js';
import { useStreamingResponse } from './hooks/useStreamingResponse.js';
import { useLocalStorage } from './hooks/useLocalStorage.js';
import { postQuery, getExampleQuestions } from './api/query.js';
import { loadSession, saveSession, clearSession } from './utils/storage.js';
import { generateUUIDv4 } from './utils/uuid.js';
import { mapHttpErrorToErrorState, mapSSEErrorToErrorState } from './utils/errorMapping.js';
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
    addAssistantMessage,
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
    const userMessage = addUserMessage(question);
    
    // Create new conversation ID if needed
    let currentConversationId = conversationId || generateUUIDv4();
    if (!conversationId) {
      setConversationId(currentConversationId);
    }

    // Create placeholder for assistant message
    const assistantMessageId = generateUUIDv4();
    let assistantContent = '';
    let assistantSources = [];
    let newConversationId = null;

    try {
      // Cancel any previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      // Post question to backend
      const response = await postQuery(question, currentConversationId);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        const errorState = mapHttpErrorToErrorState(response.status, errorBody);
        setError(errorState);
        setIsLoading(false);
        return;
      }

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
          // Update sources
          assistantSources = sources;
        },
        (errorEvent) => {
          // Handle SSE error
          const errorState = mapSSEErrorToErrorState(errorEvent.error_type, errorEvent.message);
          setError(errorState);
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
          // Handle conversation ID from start event
          newConversationId = receivedConversationId;
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

  // Add assistant message with in-progress status
  useEffect(() => {
    if (isLoading && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'user') {
        const assistantMsg = {
          id: generateUUIDv4(),
          role: 'assistant',
          content: '',
          status: 'in-progress',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    }
  }, [isLoading]);

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
