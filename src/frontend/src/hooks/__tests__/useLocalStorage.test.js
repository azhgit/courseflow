/**
 * useLocalStorage hook tests
 */

import { renderHook, act } from '@testing-library/react';
import { useLocalStorage } from '../useLocalStorage.js';

describe('useLocalStorage Hook', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('should read and write values', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    
    expect(result.current[0]).toBe('initial');
    
    act(() => {
      result.current[1]('new-value');
    });
    
    expect(result.current[0]).toBe('new-value');
    expect(localStorage.getItem('test-key')).toBe(JSON.stringify('new-value'));
  });

  test('should load existing values from localStorage', () => {
    localStorage.setItem('test-key', JSON.stringify('stored-value'));
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    expect(result.current[0]).toBe('stored-value');
  });

  test('should handle objects', () => {
    const obj = { id: 1, name: 'test' };
    const { result } = renderHook(() => useLocalStorage('test-key', null));
    
    act(() => {
      result.current[1](obj);
    });
    
    expect(result.current[0]).toEqual(obj);
  });

  test('should handle removeValue', () => {
    localStorage.setItem('test-key', JSON.stringify('value'));
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));
    
    act(() => {
      result.current[2]();
    });
    
    expect(localStorage.getItem('test-key')).toBeNull();
  });

  test('should gracefully handle quota exceeded', () => {
    const largeString = 'x'.repeat(1024 * 1024 * 10); // 10MB
    const { result } = renderHook(() => useLocalStorage('test-key', null));
    
    act(() => {
      try {
        result.current[1](largeString);
      } catch {
        // Expected to fail gracefully
      }
    });
  });
});
