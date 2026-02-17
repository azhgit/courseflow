/**
 * StreamingCursor: Blinking cursor during response streaming
 * Teal color: #14B8A6
 */
export function StreamingCursor() {
  return (
    <span className="animate-blink text-[#14B8A6]" aria-hidden="true">
      ▌
    </span>
  );
}
