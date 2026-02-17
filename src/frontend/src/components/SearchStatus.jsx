/**
 * SearchStatus: Shows "Searching..." indicator during retrieval
 */
export function SearchStatus() {
  return (
    <div className="flex items-center gap-2 text-gray-600 py-2">
      <span>🔍</span>
      <span>Searching knowledge base...</span>
    </div>
  );
}
