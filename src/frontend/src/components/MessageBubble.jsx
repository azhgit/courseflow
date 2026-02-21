import { useState } from 'react';
import { StreamingCursor } from './StreamingCursor.jsx';
import { SourceAttribution } from './SourceAttribution.jsx';
import { SourcePreview } from './SourcePreview.jsx';

/**
 * MessageBubble: Chat message bubble
 * User: right-aligned, navy bg #0F172A, white text, rounded-tr-sm speech bubble
 * AI: left-aligned, white bg, navy text, rounded-tl-sm, shadow-card
 * Max-width: 700px
 */
export function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  const [selectedSource, setSelectedSource] = useState(null);

  const handleSourceClick = (sourceName, sourcePath) => {
    setSelectedSource({ name: sourceName, path: sourcePath });
  };

  return (
    <>
      <div className={`message-fade flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <article
          className={`max-w-[700px] rounded-[20px] px-[20px] py-[16px] text-[16px] leading-relaxed ${
            isUser
              ? 'rounded-tr-sm bg-[#0F172A] text-[#FFFFFF]'
              : 'rounded-tl-sm border border-[#E2E8F0] bg-[#FFFFFF] text-[#1E293B] shadow-md'
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {message.content}
            {message.status === 'in-progress' && (
              <span className="ml-1 inline-block align-middle">
                <StreamingCursor />
              </span>
            )}
          </div>
          {!isUser && message.sources && message.status === 'complete' && (
            <SourceAttribution sources={message.sources} onSourceClick={handleSourceClick} />
          )}
        </article>
      </div>

      {/* Source Preview Modal */}
      {selectedSource && (
        <SourcePreview
          sourceName={selectedSource.name}
          sourcePath={selectedSource.path}
          onClose={() => setSelectedSource(null)}
          highlightTerms={[]}
        />
      )}
    </>
  );
}
