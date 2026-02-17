/**
 * ErrorAlert: Display error messages with retry/dismiss options
 */
export function ErrorAlert({ error, onDismiss, onRetry }) {
  return (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-800 mb-1">Error</h3>
          <p className="text-sm text-red-700">{error.message}</p>
        </div>
        <button
          onClick={onDismiss}
          className="text-red-500 hover:text-red-700 ml-4 text-lg leading-none"
        >
          ✕
        </button>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 text-xs bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
