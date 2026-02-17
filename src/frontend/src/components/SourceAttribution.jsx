/**
 * SourceAttribution: Source pills below AI messages
 * Label: 12px gray-400, pills: #F0FDFA bg with #0D9488 text
 */
export function SourceAttribution({ sources }) {
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
        return (
          <span
            key={`${label}-${idx}`}
            className="rounded-[6px] bg-[#F0FDFA] px-[10px] py-[4px] text-[12px] font-medium text-[#0D9488]"
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}
