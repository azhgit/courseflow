/**
 * EmptyState: Initial chat screen with example questions
 */
export function EmptyState({ examples = [], onExampleClick }) {
  const defaultExamples = [
    'What is photosynthesis?',
    'How does machine learning work?',
    'What are the benefits of exercise?',
    'Explain the theory of relativity',
  ];

  const displayExamples = examples.length > 0 ? examples : defaultExamples;

  return (
    <div className="flex flex-col items-center justify-center h-full p-4">
      <div className="text-center">
        <div className="mb-8 text-6xl">💬</div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">CourseFlow Chat</h2>
        <p className="text-gray-600 mb-12">
          Ask me anything and I'll search our knowledge base for the answer.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
          {displayExamples.map((example, idx) => (
            <button
              key={idx}
              onClick={() => onExampleClick(example)}
              className="p-4 bg-gray-100 hover:bg-blue-100 text-left rounded-lg border border-gray-200 hover:border-blue-300 transition-colors group"
            >
              <span className="text-gray-600 group-hover:text-blue-600 text-sm">
                {example}
              </span>
              <div className="text-gray-400 group-hover:text-blue-400 mt-2">→</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
