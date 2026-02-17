import { useState, useCallback } from 'react';

/**
 * Custom hook for parsing Server-Sent Events (SSE) streams
 * and managing streaming response state
 */
export function useStreamingResponse() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState('');
  const [sources, setSources] = useState([]);
  const [streamError, setStreamError] = useState(null);

  const parseSSEStream = useCallback(async (response, onChunk, onSources, onError, onDone) => {
    setIsStreaming(true);
    setStreamedContent('');
    setSources([]);
    setStreamError(null);

    try {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let lineBuffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        lineBuffer += chunk;

        const lines = lineBuffer.split('\n');
        lineBuffer = lines[lines.length - 1];

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const event = JSON.parse(dataStr);
              
              if (event.type === 'chunk' && event.content) {
                setStreamedContent((prev) => prev + event.content);
                onChunk?.(event.content);
              } else if (event.type === 'sources' && event.sources) {
                setSources(event.sources);
                onSources?.(event.sources);
              } else if (event.type === 'error') {
                setStreamError(event);
                onError?.(event);
              } else if (event.type === 'done') {
                onDone?.();
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }
    } catch (error) {
      setStreamError({ type: 'network_error', message: 'Connection lost' });
      onError?.(error);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return {
    isStreaming,
    streamedContent,
    sources,
    streamError,
    parseSSEStream,
  };
}
