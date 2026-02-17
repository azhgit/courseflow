import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble.jsx';
import { SearchStatus } from './SearchStatus.jsx';

/**
 * ChatHistory: Scrollable message list
 * Padding: adequate for both fixed input at bottom
 */
export function ChatHistory({ messages, isLoading }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="h-full overflow-y-auto px-6 py-6 pb-24">
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading && <SearchStatus />}
        <div ref={endRef} />
      </div>
    </div>
  );
}
