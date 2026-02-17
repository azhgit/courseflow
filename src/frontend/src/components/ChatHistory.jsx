import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble.jsx';
import { SearchStatus } from './SearchStatus.jsx';

/**
 * ChatHistory: Scrollable message history
 */
export function ChatHistory({ messages, isLoading }) {
  const endRef = useRef(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-400">
          <p>No messages yet. Start a conversation!</p>
        </div>
      ) : (
        <>
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isLoading && <SearchStatus />}
          <div ref={endRef} />
        </>
      )}
    </div>
  );
}
