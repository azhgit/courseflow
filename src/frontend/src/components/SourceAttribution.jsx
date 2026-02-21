/**
 * SourceAttribution: Clickable source pills below AI messages
 * Label: 12px gray-400, pills: #F0FDFA bg with #0D9488 text
 * Props:
 *   - sources: array of { name, path } objects
 *   - onSourceClick: function(sourceName, sourcePath)
 */
export function SourceAttribution({ sources, onSourceClick }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="mt-[12px] flex flex-wrap items-center gap-[8px] border-t border-[#E2E8F0] pt-[12px]">
      <span className="text-[12px] font-medium text-[#94A3B8]">
        Sources
      </span>
      {sources.map((source, idx) => {
        const label = typeof source?.name === 'string' ? source.name : String(source);
        const sourcePath = source?.path || source?.source || label;
        
        return (
          <button
            key={`${label}-${idx}`}
            onClick={() => onSourceClick?.(label, sourcePath)}
            className="rounded-[6px] bg-[#F0FDFA] px-[10px] py-[4px] text-[12px] font-medium text-[#0D9488] transition-colors hover:bg-[#A7F3D0] hover:text-[#065F46] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0D9488] focus-visible:ring-offset-2"
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
