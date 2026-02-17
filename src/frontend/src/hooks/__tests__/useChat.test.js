import { renderHook, act } from '@testing-library/react';
import { useChat } from '../useChat.js';

describe('useChat', () => {
  it('adds user message', () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.addUserMessage('hello');
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe('user');
    expect(result.current.messages[0].content).toBe('hello');
  });

  it('clears chat and conversation state', () => {
    const { result } = renderHook(() => useChat());

    act(() => {
      result.current.setConversationId('abc');
      result.current.addUserMessage('hello');
      result.current.clearChat();
    });

    expect(result.current.conversationId).toBeNull();
    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});
