/**
 * EmptyState: Landing page hero section
 * - No header displayed
 * - Logo, title, tagline, example cards (2×2 grid)
 * - NO input (moved to fixed bottom at app level)
 * - Full viewport height, centered content
 */
export function EmptyState({ examples = [], onExampleClick }) {
  const defaultExamples = [
    'What is photosynthesis and how does it convert light energy?',
    'Explain how async/await works in Python',
    'What were the main causes of World War II?',
    'How does machine learning differ from traditional programming?',
  ];

  const displayExamples = examples.length > 0
    ? examples.map((ex) => typeof ex === 'string' ? ex : ex.question || ex.text || String(ex))
    : defaultExamples;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl">
        {/* ── Logo: 64×64 gradient square ── */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-700 shadow-lg">
          <span className="text-2xl font-bold text-white">CF</span>
        </div>

        {/* ── Title ── */}
        <h1 className="text-center text-5xl font-bold text-gray-900">
          CourseFlow
        </h1>

        {/* ── Tagline ── */}
        <p className="mt-3 text-center text-lg text-gray-600">
          AI-powered learning assistant for any subject
        </p>

        {/* ── Example cards: 2×2 grid ── */}
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {displayExamples.map((example, idx) => (
            <button
              key={idx}
              onClick={() => onExampleClick(example)}
              className="rounded-2xl border border-gray-200 bg-white px-5 py-4 text-left shadow-sm transition-all duration-200 hover:border-teal-700 hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700 focus-visible:ring-offset-2"
            >
              <p className="text-sm font-medium text-gray-800">
                {example}
              </p>
              <p className="mt-2 text-xs text-gray-400">
                Click to ask →
              </p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
