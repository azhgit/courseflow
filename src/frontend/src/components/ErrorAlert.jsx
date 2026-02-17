/**
 * ErrorAlert: Clean error card (v2 design)
 * - Positioned at top center
 * - Red background with border
 * - X button to dismiss, Retry button
 * - No raw JSON errors displayed
 */
export function ErrorAlert({ error, onDismiss, onRetry }) {
  return (
    <div className="mx-6 mt-4 max-w-2xl rounded-2xl border border-red-200 bg-red-50 p-5 md:mx-auto">
      <div className="flex items-start justify-between gap-3 md:gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-red-100 text-sm text-red-600">
              ⚠
            </span>
            <h3 className="font-medium text-red-900 text-sm md:text-base">
              Something went wrong
            </h3>
          </div>
          <p className="mt-2 text-xs text-red-700 md:text-sm">
            {error.message}
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="flex-none text-red-400 transition-colors hover:text-red-600"
          aria-label="Dismiss error"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M13.5 2.5L2.5 13.5M2.5 2.5L13.5 13.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 w-full rounded-xl bg-gray-900 py-2 text-xs font-medium text-white transition-colors hover:bg-gray-800 md:text-sm"
        >
          Retry
        </button>
      )}
    </div>
  );
}
