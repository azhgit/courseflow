import { useState } from 'react';

/**
 * DemoNotice: Persistent notice about demo scope limitations
 * - Variant: 'banner' (full-width, always visible in EmptyState)
 * - Variant: 'collapsible' (Header, can be toggled)
 */
export function DemoNotice({ variant = 'banner', className = '' }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const bannerContent = (
    <div className="rounded-[12px] border border-[#FCD34D] bg-[#FFFBEB] px-[16px] py-[12px]">
      <div className="flex gap-[12px]">
        <div className="flex-none pt-[2px]">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="10" cy="10" r="9" stroke="#92400E" strokeWidth="1.5" />
            <text x="10" y="13" textAnchor="middle" fontSize="11" fontWeight="bold" fill="#92400E">!</text>
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-[14px] font-semibold text-[#92400E]">
            Demo Mode
          </p>
          <p className="mt-[4px] text-[13px] text-[#B45309]">
            Currently limited to built-in knowledge base (biology, programming, history, math).
            Answers are generated from internal documents only.
          </p>
        </div>
      </div>
    </div>
  );

  const collapsibleContent = (
    <div className={`border-b border-[#E2E8F0] bg-[#FFFBEB] ${className}`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-[24px] py-[12px] text-left transition-colors hover:bg-[#FEF3C7]"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-[8px]">
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="10" cy="10" r="9" stroke="#92400E" strokeWidth="1.5" />
            </svg>
            <span className="text-[13px] font-medium text-[#92400E]">
              Demo Mode: Built-in Documents Only
            </span>
          </div>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          >
            <path d="M4 6L8 10L12 6" stroke="#92400E" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-[#FCD34D] px-[24px] py-[12px]">
          <p className="text-[13px] text-[#92400E]">
            Answers are generated from internal documents in: <strong>Biology, Programming, History, Math</strong>
          </p>
        </div>
      )}
    </div>
  );

  return variant === 'banner' ? bannerContent : collapsibleContent;
}
