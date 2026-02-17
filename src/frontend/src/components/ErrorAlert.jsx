/**
 * ErrorAlert: compact error notification with retry countdown and expandable details
 */
import { useEffect, useState } from 'react';

function extractRetrySeconds(err) {
  try {
    const details = err?.error?.details || err?.details || [];
    for (const d of details) {
      if (d && d['@type'] && String(d['@type']).includes('RetryInfo')) {
        const rd = d.retryDelay || d.retry_delay || d.retry || '';
        const m = String(rd).match(/(\d+(?:\.\d*)?)s/);
        if (m) return Math.ceil(parseFloat(m[1]));
      }
    }
  } catch (e) {
    return null;
  }
  return null;
}

export function ErrorAlert({ error = {}, onDismiss, onRetry }) {
  const [open, setOpen] = useState(false);
  const retrySeconds = extractRetrySeconds(error);
  const [remaining, setRemaining] = useState(retrySeconds ?? null);

  useEffect(() => {
    setRemaining(retrySeconds ?? null);
  }, [retrySeconds]);

  useEffect(() => {
    if (remaining == null || remaining <= 0) return undefined;
    const id = setInterval(() => setRemaining((r) => (r ? r - 1 : r)), 1000);
    return () => clearInterval(id);
  }, [remaining]);

  const rawMessage = error?.error?.message || error?.message || '';
  const friendly = /quota|RESOURCE_EXHAUSTED|quota exceeded/i.test(rawMessage)
    ? '系統配額已用盡，請稍後重試或檢查專案配額。'
    : '發生錯誤，請稍後重試。';

  const copyDetails = async () => {
    const txt = JSON.stringify(error, null, 2);
    try {
      await navigator.clipboard.writeText(txt);
    } catch (e) {
      const ta = document.createElement('textarea');
      ta.value = txt;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  };

  return (
    <aside className="error-slide mx-[24px] mt-[24px] rounded-[12px] border border-red-200 bg-red-50 px-[16px] py-[12px]">
      <div className="flex items-start justify-between gap-[12px]">
        <div className="flex-1">
          <h3 className="text-[14px] font-semibold text-red-900">Request failed</h3>
          <p className="mt-[4px] text-[14px] text-red-800">{friendly}</p>
          {retrySeconds != null && (
            <p className="mt-[6px] text-[12px] text-red-700">請於 <span className="font-mono">{remaining > 0 ? `${remaining}s` : '現在'}</span> 後重試</p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <button
            onClick={onDismiss}
            className="btn-transition rounded-md p-1 text-red-600 hover:bg-red-100 hover:text-red-800"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="mt-[12px] flex items-center gap-2">
        {onRetry && (
          <button
            onClick={onRetry}
            disabled={remaining > 0}
            className={`btn-transition rounded-lg border border-red-300 bg-white px-[12px] py-[6px] text-[12px] font-semibold text-red-800 ${
              remaining > 0 ? 'opacity-60 cursor-not-allowed' : 'hover:bg-red-100'
            }`}
          >
            Retry
          </button>
        )}

        <button onClick={() => setOpen((s) => !s)} className="text-sm text-indigo-600">
          {open ? 'Hide details' : 'Show details'}
        </button>

        <button onClick={copyDetails} className="text-sm text-gray-600">
          Copy details
        </button>
      </div>

      {open && (
        <pre className="mt-3 max-h-[40vh] overflow-auto whitespace-pre-wrap break-words text-xs bg-gray-50 p-3 rounded" aria-live="polite">
          {JSON.stringify(error, null, 2)}
        </pre>
      )}
    </aside>
  );
}
