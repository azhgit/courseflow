/**
 * SearchStatus: Animated "Searching..." indicator with pulsing dots
 */
export function SearchStatus() {
  return (
    <div className="message-fade flex items-center gap-[12px]">
      <div className="inline-flex items-center gap-[6px] rounded-[12px] border border-[#E2E8F0] bg-[#FFFFFF] px-[16px] py-[12px] shadow-sm">
        <span className="h-[6px] w-[6px] animate-pulse rounded-full bg-[#0D9488]" />
        <span className="h-[6px] w-[6px] animate-pulse rounded-full bg-[#0D9488]" style={{ animationDelay: '0.2s' }} />
        <span className="h-[6px] w-[6px] animate-pulse rounded-full bg-[#0D9488]" style={{ animationDelay: '0.4s' }} />
        <span className="ml-[8px] text-[14px] text-[#475569]">Searching knowledge base…</span>
      </div>
    </div>
  );
}
