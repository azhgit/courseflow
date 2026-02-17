import { renderHook } from '@testing-library/react';
import { useStreamingResponse } from '../useStreamingResponse.js';

function streamFromText(text) {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
}

describe('useStreamingResponse', () => {
  it('parses chunk, sources, and done events', async () => {
    const payload = [
      'data: {"type":"chunk","content":"Hello"}\n',
      'data: {"type":"sources","sources":["doc-a.md"]}\n',
      'data: {"type":"done","conversation_id":"conv-1"}\n',
    ].join('');

    const response = { body: streamFromText(payload) };
    const onChunk = vi.fn();
    const onSources = vi.fn();
    const onDone = vi.fn();
    const onConversationId = vi.fn();

    const { result } = renderHook(() => useStreamingResponse());

    await result.current.parseSSEStream(
      response,
      onChunk,
      onSources,
      vi.fn(),
      onDone,
      onConversationId
    );

    expect(onChunk).toHaveBeenCalledWith('Hello');
    expect(onSources).toHaveBeenCalledWith(['doc-a.md']);
    expect(onDone).toHaveBeenCalled();
    expect(onConversationId).toHaveBeenCalledWith('conv-1');
  });
});
