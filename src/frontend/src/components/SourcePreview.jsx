import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';

export function SourcePreview({ sourceName, sourcePath, onClose, highlightTerms = [] }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const mockContent = getMockContent(sourcePath);
    setContent(mockContent);
    setLoading(false);
  }, [sourcePath]);

  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const getMockContent = (path) => {
    const mockData = {
      'docs/biology/photosynthesis.md': `# Photosynthesis

Photosynthesis is the process by which plants convert light energy into chemical energy stored in glucose.

## The Light-Dependent Reactions

The light-dependent reactions occur in the thylakoid membranes of chloroplasts:
- Photons strike chlorophyll molecules
- Electrons are excited to higher energy states
- Water molecules are split (photolysis)
- ATP and NADPH are produced

## The Calvin Cycle

The Calvin Cycle converts CO₂ into glucose using ATP and NADPH:

1. Carbon Fixation: CO₂ combines with RuBP
2. Reduction Phase: 3-PG is reduced to G3P
3. Regeneration: RuBP is regenerated

Overall equation: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂`,

      'docs/programming/python-async.md': `# Async/Await in Python

Async/await allows writing non-blocking code that handles multiple concurrent operations efficiently.

## What is Asynchronous Programming?

Asynchronous programming allows long-running operations without blocking the main thread.

## Coroutines

A coroutine is a function defined with async def that can be paused and resumed.

## Common Use Cases

- Network Requests: Fetch data from multiple URLs concurrently
- File I/O: Read/write multiple files without blocking
- Database Queries: Execute multiple queries in parallel
- Real-time Applications: Handle many concurrent connections`,

      'docs/history/wwii.md': `# World War II: Causes and Outbreak

World War II (1939-1945) was the deadliest conflict in human history.

## Treaty of Versailles (1919)

The treaty created conditions that led to WWII by humiliating Germany with reparations and territorial losses.

## Rise of Hitler

Adolf Hitler exploited Germany's economic and political crisis, promising to restore German pride.

## Immediate Causes

- Germany's invasion of Poland (September 1, 1939)
- Britain and France declare war on Germany (September 3, 1939)`,

      'docs/math/matrices.md': `# Matrix Multiplication

Matrix multiplication is fundamental in linear algebra with applications in ML and computer graphics.

## Definition

If A is m×n and B is n×p, then AB is an m×p matrix where each element is a dot product.

## Properties

- Not Commutative: AB ≠ BA
- Associative: (AB)C = A(BC)
- Identity Matrix: AI = A`,
    };

    return mockData[path] || null;
  };

  const highlightContent = (text, terms) => {
    if (!text || terms.length === 0) return text;
    let result = text;
    terms.forEach((term) => {
      const regex = new RegExp(`(${term})`, 'gi');
      result = result.replace(
        regex,
        '<mark style="background-color:#FCD34D;padding:2px 4px;border-radius:2px;">$1</mark>'
      );
    });
    return result;
  };

  const renderContent = (text) => {
    const lines = highlightContent(text, highlightTerms).split('\n');
    const output = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (line.startsWith('### ')) { output.push(`<h3 style="font-size:15px;font-weight:600;color:#0F172A;margin:16px 0 6px;">${line.slice(4)}</h3>`); i++; continue; }
      if (line.startsWith('## '))  { output.push(`<h2 style="font-size:17px;font-weight:600;color:#0F172A;margin:20px 0 8px;">${line.slice(3)}</h2>`); i++; continue; }
      if (line.startsWith('# '))   { output.push(`<h1 style="font-size:20px;font-weight:700;color:#0F172A;margin:0 0 14px;">${line.slice(2)}</h1>`); i++; continue; }
      if (line.startsWith('- ')) {
        const items = [];
        while (i < lines.length && lines[i].startsWith('- ')) { items.push(`<li style="margin:4px 0;color:#334155;">${lines[i].slice(2)}</li>`); i++; }
        output.push(`<ul style="margin:8px 0 12px;padding-left:20px;list-style-type:disc;">${items.join('')}</ul>`);
        continue;
      }
      if (/^\d+\.\s/.test(line)) {
        const items = [];
        while (i < lines.length && /^\d+\.\s/.test(lines[i])) { items.push(`<li style="margin:4px 0;color:#334155;">${lines[i].replace(/^\d+\.\s/, '')}</li>`); i++; }
        output.push(`<ol style="margin:8px 0 12px;padding-left:20px;list-style-type:decimal;">${items.join('')}</ol>`);
        continue;
      }
      if (line === '') { output.push('<br />'); i++; continue; }
      output.push(`<p style="margin:0 0 10px;color:#334155;line-height:1.6;">${line}</p>`);
      i++;
    }
    return output.join('');
  };

  // Responsive breakpoint: treat >=768px as "desktop/tablet" mode
  const isWide = true; // 所有裝置統一置中顯示

  if (typeof document === 'undefined') return null;

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        style={{ position: 'fixed', inset: 0, zIndex: 9999, backgroundColor: 'rgba(0,0,0,0.6)' }}
        onClick={onClose}
      />

      {/*
        Outer positioner: full-screen flex container
        - Mobile (<768px):  align to bottom
        - Tablet/Desktop (>=768px): center both axes
        All in inline style → no Tailwind JIT dependency
      */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 10000,
          display: 'flex',
          alignItems: isWide ? 'center' : 'flex-end',
          justifyContent: isWide ? 'center' : 'stretch',
          pointerEvents: 'none',
        }}
      >
        {/*
          Modal panel
          - Mobile:  full width, 75vh height, rounded top only
          - Tablet+: max 600px wide, auto height capped at 85vh, fully rounded
        */}
        <div
          style={{
            pointerEvents: 'auto',
            display: 'flex',
            flexDirection: 'column',
            width: 'calc(100% - 32px)',
            maxWidth: '600px',
            maxHeight: '85vh',
            overflow: 'hidden',
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            boxShadow: '0 8px 40px rgba(0,0,0,0.2)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div style={{
            flexShrink: 0,
            borderBottom: '1px solid #E2E8F0',
            padding: '16px 24px',
            backgroundColor: '#ffffff',
          }}>
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <h2 className="truncate text-[18px] font-semibold text-[#0F172A]">
                  {sourceName}
                </h2>
                <p className="truncate text-[12px] text-[#94A3B8]">{sourcePath}</p>
              </div>
              <button
                onClick={onClose}
                className="ml-4 flex h-8 w-8 flex-none items-center justify-center rounded-lg bg-[#F1F5F9] text-[#475569] transition-colors hover:bg-[#E2E8F0]"
                aria-label="Close"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>

          {/* Scrollable Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
            {loading && (
              <div className="flex items-center justify-center py-10">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#E2E8F0] border-t-[#0D9488]" />
              </div>
            )}
            {error && (
              <div className="rounded-lg border border-[#FEE2E2] bg-[#FEF2F2] px-3 py-3">
                <p className="text-[13px] text-[#DC2626]">{error}</p>
              </div>
            )}
            {content && !loading && (
              <div dangerouslySetInnerHTML={{ __html: renderContent(content) }} />
            )}
            {!content && !loading && !error && (
              <div className="flex items-center justify-center py-10">
                <p className="text-[14px] text-[#94A3B8]">No content available</p>
              </div>
            )}
          </div>

        </div>{/* end modal panel */}
      </div>{/* end positioner */}
    </>,
    document.body
  );
}