import { useState, useRef } from 'react';

/**
 * ChatInput: Fixed bottom input for chat page
 * - Position: fixed bottom of viewport
 * - Container: 900px centered with padding
 * - Input: Navy send button, teal focus ring
 * - Only visible when NOT on empty state (showEmptyState = false)
 */
export function ChatInput({ onSubmit, isDisabled = false }) {
  const [input, setInput] = useState('');
  const inputRef = useRef(null);

  const canSend = input.trim().length > 0 && !isDisabled;

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    onSubmit(trimmed);
    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-[#E2E8F0] bg-[#FFFFFF] shadow-sm">
      <div className="mx-auto max-w-[900px] px-[24px] py-[24px]">
        <div className="flex items-center gap-[12px]">
          <label htmlFor="chat-input" className="sr-only">
            Ask a follow-up question
          </label>
          <input
            id="chat-input"
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a follow-up question…"
            disabled={isDisabled}
            autoComplete="off"
            className="input-focus flex-1 rounded-[12px] border border-[#E2E8F0] bg-[#FFFFFF] px-[16px] py-[12px] text-[16px] text-[#0F172A] placeholder:text-[#94A3B8] focus:outline-none disabled:cursor-not-allowed disabled:bg-[#F8FAFC] disabled:text-[#94A3B8]"
          />
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            aria-label="Send message"
            className="btn-transition flex h-[48px] w-[48px] flex-none items-center justify-center rounded-[12px] bg-[#1E293B] text-[#FFFFFF] transition-colors duration-150 hover:bg-[#0F172A] disabled:cursor-not-allowed disabled:bg-[#E2E8F0] disabled:text-[#94A3B8]"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M10 17V3M10 3L4.5 8.5M10 3L15.5 8.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
