/**
 * Header: Clean navigation bar (sticky)
 * - Minimal style: no background color, no border
 * - Left: Logo icon (32px) + "CourseFlow" text (clickable, returns to home)
 * - Right: "New Chat" button
 * - v2 Design: clean aesthetic, opacity hover effect
 */
export function Header({ onNewChat, onReturnHome }) {
  return (
    <header className="sticky top-0 z-50 bg-white px-6 py-3">
      <div className="flex items-center justify-between">
        {/* ── Left: Clickable logo + brand name ── */}
        <button
          onClick={onReturnHome}
          className="flex items-center gap-2 transition-opacity duration-200 hover:opacity-70"
          aria-label="Return to home"
        >
          {/* Logo: 32px square with teal background */}
          <div className="flex h-8 w-8 flex-none items-center justify-center rounded-lg bg-teal-700">
            <span className="text-sm font-bold text-white">CF</span>
          </div>

          {/* Brand name */}
          <span className="text-lg font-semibold text-gray-900">
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
 * NewChatButton: "New Chat" button with v2 Modal confirmation
 * Modal: centered, semi-transparent background, clean card design
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
        className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700 focus-visible:ring-offset-2"
      >
        New Chat
      </button>

      {showConfirmation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-6">
          <div className="w-full max-w-80 rounded-2xl bg-white p-6 shadow-xl animation-fadeIn">
            <h3 className="mb-2 text-lg font-semibold text-gray-900">
              Start a new chat?
            </h3>
            <p className="mb-6 text-sm text-gray-500">
              Current conversation will be cleared.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirmation(false)}
                className="flex-1 rounded-lg border border-gray-200 bg-white py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="flex-1 rounded-lg bg-teal-700 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-800"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
