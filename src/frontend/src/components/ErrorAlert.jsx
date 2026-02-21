/**
 * ErrorAlert: compact error notification with retry countdown and expandable details
 */
import { useEffect, useState } from 'react';

function extractRetrySeconds(err) {
  // Robustly search the error object for a retryDelay like '20s' and return seconds
  try {
    const queue = [err?.error, err?.details, err?.error?.details, err];
    const seen = new Set();
    while (queue.length) {
      const node = queue.shift();
      if (!node || seen.has(node)) continue;
      seen.add(node);
      if (typeof node === 'string') {
        const m = node.match(/(\d+(?:\.\d*)?)s/);
        if (m) return Math.ceil(parseFloat(m[1]));
      } else if (typeof node === 'object') {
        for (const k of Object.keys(node)) {
          const v = node[k];
          if (typeof v === 'string') {
            const m = v.match(/(\d+(?:\.\d*)?)s/);
            if (m) return Math.ceil(parseFloat(m[1]));
          } else if (typeof v === 'object') {
            queue.push(v);
          }
        }
      }
    }
  } catch (e) {
    return null;
  }
  return null;
}

export function ErrorAlert({ error = {}, onDismiss, onRetry }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
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
  const quotaLike = /quota|RESOURCE_EXHAUSTED|quota exceeded|rate limit/i.test(rawMessage);
  const source = error?.source || error?.error?.details?.source;
  const sourceLabel = source === 'local_guard' ? 'Local guard' : source === 'gemini' ? 'Gemini' : null;
  const friendly = quotaLike
    ? `${sourceLabel ? `${sourceLabel} ` : ''}quota/rate limit reached. Please wait and retry.`
    : 'Something went wrong. Please try again.';

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
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <aside className="mx-[24px] mt-[24px] rounded-[16px] border border-red-100 bg-white shadow-sm px-[20px] py-[16px]">
      {/* ── Top row: title + dismiss ── */}
      <div className="flex items-start justify-between gap-[12px]">
        <div className="flex items-center gap-[8px]">
          {/* Error icon */}
          <div className="flex h-[32px] w-[32px] flex-none items-center justify-center rounded-full bg-red-50">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 5v4M8 11h.01" stroke="#DC2626" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="8" cy="8" r="6.5" stroke="#DC2626" strokeWidth="1.5"/>
            </svg>
          </div>
          <div>
            <h3 className="text-[14px] font-semibold text-[#0F172A]">Request failed</h3>
            <p className="text-[13px] text-[#64748B]">{friendly}</p>
          </div>
        </div>

        {/* Dismiss X */}
        <button
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="flex h-[28px] w-[28px] flex-none items-center justify-center rounded-full text-[#94A3B8] transition hover:bg-[#F1F5F9] hover:text-[#475569]"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      {/* ── Retry countdown ── */}
      {retrySeconds != null && remaining > 0 && (
        <p className="mt-[10px] text-[12px] text-[#94A3B8]">
          You can retry in{' '}
          <span className="font-mono font-medium text-[#475569]">{remaining}s</span>
        </p>
      )}

      {/* ── Action row: details actions first, retry below ── */}
      <div className="mt-[14px]">
        <div className="flex items-center gap-[8px]">
          {/* Show/Hide details */}
          <button
            onClick={() => setOpen((s) => !s)}
            className="rounded-[10px] border border-[#E2E8F0] bg-white px-[14px] py-[7px] text-[13px] font-medium text-[#475569] transition hover:bg-[#F8FAFC]"
          >
            {open ? 'Hide details' : 'Show details'}
          </button>

          {/* Copy details */}
          <button
            onClick={copyDetails}
            className="rounded-[10px] border border-[#E2E8F0] bg-white px-[14px] py-[7px] text-[13px] font-medium text-[#475569] transition hover:bg-[#F8FAFC]"
          >
            {copied ? '✓ Copied' : 'Copy details'}
          </button>
        </div>

        {/* ── Expandable raw details ── */}
        {open && (
          <pre className="mt-[12px] max-h-[200px] overflow-auto whitespace-pre-wrap break-words rounded-[10px] bg-[#F8FAFC] p-[12px] text-[11px] text-[#64748B]">
            {JSON.stringify(error, null, 2)}
          </pre>
        )}

        {onRetry && (
          <div className="mt-[12px]">
            <button
              onClick={onRetry}
              disabled={remaining > 0}
              className={`rounded-[10px] px-[14px] py-[7px] text-[13px] font-medium ${
                remaining > 0
                  ? 'bg-[#94A3B8] cursor-not-allowed'
                  : 'bg-[#0D9488] hover:bg-[#0B7A6F]'
              }`}
              style={{ color: '#ffffff', WebkitTextFillColor: '#ffffff' }}
            >
              {remaining > 0 ? `Retry in ${remaining}s` : 'Retry'}
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
