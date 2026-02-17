/**
 * NewChatButton: Button to start a new conversation with confirmation
 */
import { useState } from 'react';

export function NewChatButton({ onNewChat }) {
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleConfirm = () => {
    onNewChat();
    setShowConfirmation(false);
  };

  return (
    <>
      <button
        onClick={() => setShowConfirmation(true)}
        className="px-4 py-2 bg-blue-700 hover:bg-blue-800 rounded-lg text-sm font-medium transition-colors"
      >
        New Chat
      </button>

      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-semibold mb-2">Start New Chat?</h3>
            <p className="text-gray-600 mb-6">This will clear your current conversation history.</p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={() => setShowConfirmation(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Clear History
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
