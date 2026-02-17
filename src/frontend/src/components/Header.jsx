/**
 * Header: Modern SaaS navigation bar (sticky)
 * - Left: Logo icon (32px) + "CourseFlow" text (clickable, returns to home)
 * - Right: "New Chat" button
 * - Sticky positioning with shadow
 */
export function Header({ onNewChat, onReturnHome }) {
  return (
    <header className="sticky top-0 z-40">
      <div className="mx-auto flex h-[72px] max-w-full items-center justify-between px-[24px]">
        {/* ── Left: Clickable logo + brand name ── */}
        <button
          onClick={onReturnHome}
          className="btn-transition flex items-center gap-[12px] rounded-lg hover:opacity-80"
          aria-label="Return to home"
        >
          {/* Logo: 32px square with navy-to-teal gradient */}
          <div className="flex h-[32px] w-[32px] flex-none items-center justify-center rounded-[8px] bg-gradient-to-br from-[#0F172A] to-[#0D9488]">
            <span className="text-[14px] font-bold text-[#FFFFFF]">CF</span>
          </div>

          {/* Brand name */}
          <span className="font-sans text-[18px] font-semibold text-[#0F172A]">
            CourseFlow
          </span>
        </button>

        {/* ── Right: New Chat Button ── */}
        <NewChatButton onNewChat={onNewChat} />
      </div>
    </header>
  );
}

import { useState } from 'react';

/**
 * NewChatButton: "New Chat" button with confirmation modal
 * Always visible (no condition)
 */
function NewChatButton({ onNewChat }) {
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleConfirm = () => {
    onNewChat();
    setShowConfirmation(false);
  };

  return (
    <>
      <button
        onClick={() => setShowConfirmation(true)}
        className="btn-transition rounded-[8px] border border-[#E2E8F0] bg-[#FFFFFF] px-[16px] py-[8px] text-[14px] font-semibold text-[#334155] hover:border-[#0D9488] hover:bg-[#F8FAFC] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0D9488] focus-visible:ring-offset-2"
      >
        New Chat
      </button>

      {showConfirmation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/30 px-[24px] backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-[16px] border border-[#E2E8F0] bg-[#FFFFFF] p-[24px] shadow-lg animation-fadeIn">
            <h3 className="font-sans text-[24px] font-bold text-[#0F172A]">
              Start a new chat?
            </h3>
            <p className="mt-[12px] text-[16px] leading-relaxed text-[#475569]">
              This will clear the current conversation history from this session.
            </p>
            <div className="mt-[24px] flex justify-end gap-[12px]">
              <button
                onClick={() => setShowConfirmation(false)}
                className="btn-transition rounded-[8px] border border-[#E2E8F0] bg-[#FFFFFF] px-[16px] py-[8px] text-[14px] font-medium text-[#475569] hover:bg-[#F8FAFC]"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="btn-transition rounded-[8px] bg-[#1E293B] px-[16px] py-[8px] text-[14px] font-medium text-[#FFFFFF] hover:bg-[#0F172A]"
              >
                Clear history
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
