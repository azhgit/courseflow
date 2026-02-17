import { useState, useRef } from 'react';

/**
 * FixedInput: Universal sticky bottom input for landing and chat pages
 * v2 Design:
 * - position: fixed; bottom: 0; left: 0; right: 0
 * - White background with subtle top shadow
 * - max-width: 768px, centered
 * - Placeholder changes based on page context
 */
export function FixedInput({ onSubmit, isDisabled = false, placeholder = 'Ask a question about your course content…' }) {
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
    <div className="fixed bottom-0 left-0 right-0 z-30 bg-white shadow-[0_-1px_8px_rgba(0,0,0,0.06)] pb-4 pt-3 md:pb-6 md:pt-4">
      <div className="mx-auto max-w-2xl px-6">
        <div className="flex gap-2">
          <label htmlFor="fixed-input" className="sr-only">
            {placeholder}
          </label>
          <input
            id="fixed-input"
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isDisabled}
            autoComplete="off"
            className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-3 text-gray-800 placeholder:text-gray-400 focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-700/20 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
          />
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            aria-label="Send message"
            className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-gray-900 text-white transition-colors hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400 md:h-12 md:w-12"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 17V3M10 3L4.5 8.5M10 3L15.5 8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
