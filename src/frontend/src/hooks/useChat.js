import { useState, useCallback } from 'react';
import { generateUUIDv4 } from '../utils/uuid.js';

/**
 * Custom hook for managing chat state
 */
export function useChat() {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const addUserMessage = useCallback((content) => {
    const message = {
      id: generateUUIDv4(),
      role: 'user',
      content,
      status: 'complete',
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  const addAssistantMessage = useCallback((content, sources = []) => {
    const message = {
      id: generateUUIDv4(),
      role: 'assistant',
      content,
      sources,
      status: 'complete',
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  return {
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
    clearChat,
  };
}
