import { StreamingCursor } from './StreamingCursor.jsx';
import { SourceAttribution } from './SourceAttribution.jsx';

/**
 * MessageBubble: Individual chat message (user or assistant)
 */
export function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-xs px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-none'
            : 'bg-gray-200 text-gray-900 rounded-bl-none'
        }`}
      >
        <div className="whitespace-pre-wrap break-words">
          {message.content}
          {message.status === 'in-progress' && (
            <span className="ml-1">
              <StreamingCursor />
            </span>
          )}
        </div>
        {!isUser && message.sources && message.status === 'complete' && (
          <SourceAttribution sources={message.sources} />
        )}
      </div>
    </div>
  );
}
