import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';

export function NewChatButton({ onNewChat }) {
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const handleConfirm = () => {
    onNewChat();
    setShowConfirmation(false);
  };

  const modal = (
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(15,23,42,0.3)', padding: '0 24px' }}
      onClick={(e) => { if (e.target === e.currentTarget) setShowConfirmation(false); }}
    >
      <div style={{ width: '100%', maxWidth: '384px', borderRadius: '16px', backgroundColor: '#fff', padding: '24px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
        <h3 style={{ fontSize: '24px', fontWeight: 700, color: '#0F172A', margin: 0 }}>Start a new chat?</h3>
        <p style={{ marginTop: '12px', fontSize: '16px', color: '#475569', lineHeight: 1.6 }}>
          This will clear the current conversation history from this session.
        </p>
        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            onClick={() => setShowConfirmation(false)}
            style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid #E2E8F0', background: '#fff', fontSize: '14px', cursor: 'pointer', color: '#475569' }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            style={{ padding: '8px 16px', borderRadius: '8px', border: 'none', background: '#1E293B', color: '#fff', fontSize: '14px', cursor: 'pointer' }}
          >
            Clear history
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button
        onClick={() => setShowConfirmation(true)}
        className="btn-transition rounded-[8px] border border-[#E2E8F0] bg-[#FFFFFF] px-[16px] py-[8px] text-[14px] font-semibold text-[#334155] hover:border-[#0D9488] hover:bg-[#F8FAFC]"
      >
        New Chat
      </button>
      {mounted && showConfirmation && createPortal(modal, document.body)}
    </>
  );
}