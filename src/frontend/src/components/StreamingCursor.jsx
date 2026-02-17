/**
 * StreamingCursor: Blinking cursor for in-progress messages
 */
export function StreamingCursor() {
  return (
    <span className="inline-block animate-blink text-lg">
      ▌
    </span>
  );
}
