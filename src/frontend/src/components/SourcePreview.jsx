import { useState, useEffect } from 'react';

/**
 * SourcePreview: Modal drawer showing source document content
 * Props:
 *   - sourceName: string (e.g., 'photosynthesis.md')
 *   - sourcePath: string (e.g., 'docs/biology/photosynthesis.md')
 *   - onClose: function to close modal
 *   - highlightTerms: array of strings to highlight in content
 */
export function SourcePreview({ sourceName, sourcePath, onClose, highlightTerms = [] }) {
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // TODO: Replace with actual API call to /api/v1/source/{path}
    // For now, using mock data
    const mockContent = getMockContent(sourcePath);
    setContent(mockContent);
    setLoading(false);
  }, [sourcePath]);

  const getMockContent = (path) => {
    const mockData = {
      'docs/biology/photosynthesis.md': `# Photosynthesis

Photosynthesis is the process by which plants convert light energy (from the sun) into chemical energy stored in glucose. This process is fundamental to life on Earth and occurs primarily in the leaves of green plants.

## The Light-Dependent Reactions

The light-dependent reactions occur in the thylakoid membranes of chloroplasts. During this stage:
- Photons strike chlorophyll molecules
- Electrons are excited to higher energy states
- Water molecules are split (photolysis)
- ATP and NADPH are produced

## The Light-Independent Reactions (Calvin Cycle)

The Calvin Cycle occurs in the stroma of chloroplasts and converts CO₂ into glucose using the ATP and NADPH produced in the light reactions. It consists of three main phases:

1. **Carbon Fixation**: CO₂ combines with RuBP
2. **Reduction Phase**: 3-PG is reduced to G3P
3. **Regeneration**: RuBP is regenerated from G3P

## Equation

The overall equation for photosynthesis is:
\`\`\`
6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂
\`\`\`

This process is essential for:
- Producing oxygen for respiration
- Creating glucose for plant growth
- Supporting food chains and ecosystems`,

      'docs/programming/python-async.md': `# Async/Await in Python

Async/await is a pattern for writing asynchronous code in Python. It allows you to write non-blocking code that can handle multiple concurrent operations efficiently.

## What is Asynchronous Programming?

Asynchronous programming allows a program to perform long-running operations without blocking the main thread. Instead of waiting for an operation to complete, the program can continue executing other code.

## Coroutines

A coroutine is a function that can be paused and resumed. In Python, you define a coroutine using the \`async def\` keyword:

\`\`\`python
async def fetch_data(url):
    # This is a coroutine
    response = await some_http_library.get(url)
    return response
\`\`\`

## The await Keyword

The \`await\` keyword pauses the coroutine until the awaited operation completes:

\`\`\`python
async def main():
    result = await fetch_data('https://example.com')
    print(result)
\`\`\`

## Event Loop

The event loop is the core of async programming in Python. It manages the execution of coroutines and handles I/O operations efficiently.

## Common Use Cases

- **Network Requests**: Fetch data from multiple URLs concurrently
- **File I/O**: Read/write multiple files without blocking
- **Database Queries**: Execute multiple queries in parallel
- **Real-time Applications**: Handle many concurrent connections`,

      'docs/history/wwii.md': `# World War II: Causes and Outbreak

World War II (1939-1945) was the deadliest and most destructive conflict in human history. Understanding its causes is essential to understanding modern history.

## Treaty of Versailles (1919)

The Treaty of Versailles ending World War I created conditions that led to WWII:
- Germany forced to pay massive reparations
- German territories reduced significantly
- German military severely limited
- Germans felt humiliated and resentful

## Economic Instability

The Great Depression (1929-1930s) devastated economies worldwide:
- Germany was particularly hard hit
- Mass unemployment created social unrest
- Economic desperation fueled extremism
- People sought strong leadership and scapegoats

## Rise of Hitler and Nazi Party

Adolf Hitler exploited Germany's economic and political crisis:
- Promised to restore German pride and prosperity
- Blamed Germany's problems on Jews and communists
- Offered nationalist ideology and territorial expansion
- Appealed to middle class and working class Germans

## Failure of Collective Security

The League of Nations failed to prevent aggression:
- Japan invaded Manchuria (1931)
- Italy invaded Ethiopia (1935)
- Germany remilitarized the Rhineland (1936)
- No effective international response

## Immediate Causes

- Germany's annexation of Austria (Anschluss, 1938)
- Munich Agreement allowing German expansion (1938)
- Germany's invasion of Poland (September 1, 1939)
- Britain and France declare war on Germany (September 3, 1939)`,

      'docs/math/matrices.md': `# Matrix Multiplication

Matrix multiplication is a fundamental operation in linear algebra with applications in computer graphics, physics, and machine learning.

## Definition

If A is an m×n matrix and B is an n×p matrix, then the product AB is an m×p matrix where:

\`\`\`
(AB)ᵢⱼ = Σₖ Aᵢₖ × Bₖⱼ
\`\`\`

The element at position (i,j) in the product is the dot product of row i of A and column j of B.

## When is Matrix Multiplication Defined?

Matrix multiplication A×B is only defined when:
- The number of columns in A equals the number of rows in B
- If A is m×n, then B must be n×p
- The result is an m×p matrix

## Example

\`\`\`
A = [1 2]    B = [5 6]     AB = [1×5+2×7  1×6+2×8]   = [19 22]
    [3 4]        [7 8]          [3×5+4×7  3×6+4×8]     [43 50]
\`\`\`

## Properties

- **Not Commutative**: AB ≠ BA (in general)
- **Associative**: (AB)C = A(BC)
- **Distributive**: A(B+C) = AB + AC
- **Identity Matrix**: AI = A

## Applications

- Computer Graphics: Transformations (rotation, scaling, translation)
- Physics: Quantum mechanics and dynamics
- Machine Learning: Neural network computations
- Data Analysis: Dimension reduction and transformations`,
    };

    return mockData[path] || null;
  };

  const highlightContent = (text, terms) => {
    if (!text || terms.length === 0) return text;

    let highlightedText = text;
    terms.forEach((term) => {
      const regex = new RegExp(`(${term})`, 'gi');
      highlightedText = highlightedText.replace(
        regex,
        '<mark style="background-color: #FCD34D; padding: 2px 4px; border-radius: 2px;">$1</mark>'
      );
    });

    return highlightedText;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/50 md:items-center">
      {/* Modal Backdrop */}
      <button
        onClick={onClose}
        className="absolute inset-0"
        aria-label="Close modal"
      />

      {/* Drawer/Modal */}
      <div className="relative w-full max-h-[90vh] overflow-hidden rounded-t-[16px] bg-white md:max-w-[600px] md:rounded-[16px]">
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-[#E2E8F0] bg-white px-[24px] py-[16px]">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <h2 className="truncate text-[18px] font-semibold text-[#0F172A]">
                {sourceName}
              </h2>
              <p className="truncate text-[12px] text-[#94A3B8]">
                {sourcePath}
              </p>
            </div>
            <button
              onClick={onClose}
              className="ml-[16px] flex h-[32px] w-[32px] flex-none items-center justify-center rounded-[8px] bg-[#F1F5F9] text-[#475569] transition-colors hover:bg-[#E2E8F0]"
              aria-label="Close"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto px-[24px] py-[16px] max-h-[calc(90vh-80px)]">
          {loading && (
            <div className="flex items-center justify-center py-[40px]">
              <div className="h-[24px] w-[24px] animate-spin rounded-full border-[2px] border-[#E2E8F0] border-t-[#0D9488]" />
            </div>
          )}

          {error && (
            <div className="rounded-[8px] border border-[#FEE2E2] bg-[#FEF2F2] px-[12px] py-[12px]">
              <p className="text-[13px] text-[#DC2626]">{error}</p>
            </div>
          )}

          {content && !loading && (
            <div className="prose prose-sm max-w-none">
              <div
                className="text-[14px] leading-[1.6] text-[#334155]"
                dangerouslySetInnerHTML={{
                  __html: highlightContent(content, highlightTerms)
                    .split('\n')
                    .map((line, idx) => {
                      if (line.startsWith('#')) {
                        const level = line.match(/^#+/)[0].length;
                        return `<h${level} class="text-[${18 - level * 2}px] font-semibold text-[#0F172A] mt-[16px] mb-[8px]">${line.replace(/^#+\s/, '')}</h${level}>`;
                      }
                      if (line.startsWith('```')) {
                        return '<div class="bg-[#F1F5F9] rounded-[6px] p-[12px] my-[8px] overflow-x-auto"><code class="text-[12px] font-mono text-[#334155]">';
                      }
                      if (line === '') return '<br />';
                      return `<p class="mb-[12px]">${line}</p>`;
                    })
                    .join('')
                }}
              />
            </div>
          )}

          {!content && !loading && !error && (
            <div className="flex items-center justify-center py-[40px]">
              <p className="text-[14px] text-[#94A3B8]">No content available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
