/**
 * SourceAttribution: Display source documents below assistant message
 */
export function SourceAttribution({ sources }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 pt-2 border-t border-gray-200 text-sm text-gray-600">
      <span className="font-semibold">Sources: </span>
      <span>
        {sources.map((source, idx) => (
          <span key={idx}>
            {idx > 0 && ', '}
            <span className="italic">{source.name}</span>
          </span>
        ))}
      </span>
    </div>
  );
}
