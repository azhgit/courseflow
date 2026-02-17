/**
 * EmptyState: Landing page with hero section + cards + input
 * No header — full screen experience
 * Input at bottom (sticky footer)
 */
export function EmptyState({ examples = [], onExampleClick, onSubmit, isDisabled = false }) {
  const defaultExamples = [
    'What is photosynthesis and how does it convert light energy?',
    'Explain how async/await works in Python',
    'What were the main causes of World War II?',
    'How does machine learning differ from traditional programming?',
  ];

  const displayExamples = examples.length > 0
    ? examples.map((ex) => typeof ex === 'string' ? ex : ex.question || ex.text || String(ex))
    : defaultExamples;

  return (
    <div className="flex h-full flex-col">
      {/* ── Hero section (scrollable) ── */}
      <div className="flex flex-1 items-center justify-center overflow-y-auto px-[24px] py-[64px]">
        <div className="w-full max-w-[700px]">
          {/* ── Logo: 64×64 gradient square ── */}
          <div className="mx-auto mb-[24px] flex h-[64px] w-[64px] items-center justify-center rounded-[16px] bg-gradient-to-br from-[#0F172A] to-[#0D9488] shadow-lg">
            <span className="font-sans text-[32px] font-bold text-[#FFFFFF]">CF</span>
          </div>

          {/* ── Title ── */}
          <h1 className="font-sans text-[48px] font-bold text-[#0F172A]">
            CourseFlow
          </h1>

          {/* ── Tagline ── */}
          <p className="mx-auto mt-[12px] max-w-[500px] text-[18px] font-normal text-[#475569]">
            AI-powered learning assistant for any subject
          </p>

          {/* ── Example cards: 2×2 grid ── */}
          <div className="mt-[48px] grid grid-cols-1 gap-[16px] sm:grid-cols-2">
            {displayExamples.map((example, idx) => (
              <button
                key={idx}
                onClick={() => onExampleClick(example)}
                className="hover-lift group cursor-pointer rounded-[16px] border border-[#E2E8F0] bg-[#FFFFFF] px-[20px] py-[20px] text-left shadow-sm transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0D9488] focus-visible:ring-offset-2"
              >
                <p className="text-[16px] font-medium text-[#334155]">
                  {example}
                </p>
                <p className="mt-[8px] text-[12px] text-[#94A3B8]">
                  Click to ask →
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Input footer (sticky bottom) ── */}
      <div className="flex-none border-t border-[#E2E8F0] bg-[#FFFFFF] shadow-sm">
        <div className="mx-auto max-w-[900px] px-[24px] py-[24px]">
          <LandingPageInput onSubmit={onSubmit} isDisabled={isDisabled} />
        </div>
      </div>
    </div>
  );
}

/**
 * LandingPageInput: Input component for landing page
 * Integrated with EmptyState
 */
import { useState, useRef } from 'react';

function LandingPageInput({ onSubmit, isDisabled = false }) {
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
    <div className="flex items-center gap-[12px]">
      <label htmlFor="landing-input" className="sr-only">
        Ask your question
      </label>
      <input
        id="landing-input"
        ref={inputRef}
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about your course content…"
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
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 17V3M10 3L4.5 8.5M10 3L15.5 8.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
    </div>
  );
}
