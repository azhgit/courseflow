/**
 * ErrorAlert: Error notification banner
 * Slides down, red-tinted, with dismiss + retry
 */
export function ErrorAlert({ error, onDismiss, onRetry }) {
  return (
    <aside className="error-slide mx-[24px] mt-[24px] rounded-[12px] border border-red-200 bg-red-50 px-[16px] py-[12px]">
      <div className="flex items-start justify-between gap-[12px]">
        <div className="flex-1">
          <h3 className="text-[14px] font-semibold text-red-900">Request failed</h3>
          <p className="mt-[4px] text-[14px] text-red-800">{error.message}</p>
        </div>
        <button
          onClick={onDismiss}
          className="btn-transition flex-none rounded-md p-1 text-red-600 hover:bg-red-100 hover:text-red-800"
          aria-label="Dismiss error"
        >
          ✕
        </button>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn-transition mt-[12px] rounded-lg border border-red-300 bg-[#FFFFFF] px-[12px] py-[6px] text-[12px] font-semibold text-red-800 hover:bg-red-100"
        >
          Retry
        </button>
      )}
    </aside>
  );
}
