import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble.jsx';
import { SearchStatus } from './SearchStatus.jsx';

/**
 * ChatHistory: Scrollable message list
 * Padding: 24px, max-width: 900px, centered
 * Padding-bottom: 120px for fixed input
 */
export function ChatHistory({ messages, isLoading }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="h-full overflow-y-auto px-[24px] py-[24px] pb-[140px]">
      <div className="mx-auto flex max-w-[900px] flex-col gap-[24px]">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading && <SearchStatus />}
        <div ref={endRef} />
      </div>
    </div>
  );
}
