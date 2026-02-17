/**
 * Validation function tests
 */

import {
  isValidUUID,
  isValidISO8601,
  isValidChatSession,
  isValidMessage,
  isValidSource,
  isValidErrorState,
} from '../validation.js';

describe('Validation Functions', () => {
  // UUID validation
  test('isValidUUID should validate correct UUIDs', () => {
    const validUUID = '550e8400-e29b-4000-a000-000000000000';
    expect(isValidUUID(validUUID)).toBe(true);
  });

  test('isValidUUID should reject invalid UUIDs', () => {
    expect(isValidUUID('not-a-uuid')).toBe(false);
    expect(isValidUUID('550e8400-e29b-3000-a000-000000000000')).toBe(false); // Wrong version
    expect(isValidUUID('')).toBe(false);
    expect(isValidUUID(null)).toBe(false);
  });

  // ISO8601 validation
  test('isValidISO8601 should validate correct timestamps', () => {
    expect(isValidISO8601('2026-02-17T10:30:00Z')).toBe(true);
  });

  test('isValidISO8601 should reject invalid timestamps', () => {
    expect(isValidISO8601('2026-02-17')).toBe(false);
    expect(isValidISO8601('not-a-date')).toBe(false);
    expect(isValidISO8601('')).toBe(false);
  });

  // Chat session validation
  test('isValidChatSession should validate complete session', () => {
    const session = {
      conversation_id: '550e8400-e29b-4000-a000-000000000000',
      messages: [
        {
          id: '550e8400-e29b-4000-a000-000000000001',
          role: 'user',
          content: 'Hello',
          status: 'complete',
          timestamp: '2026-02-17T10:30:00Z',
        },
      ],
      created_at: '2026-02-17T10:30:00Z',
      updated_at: '2026-02-17T10:30:00Z',
    };
    expect(isValidChatSession(session)).toBe(true);
  });

  // Message validation
  test('isValidMessage should validate correct messages', () => {
    const message = {
      id: '550e8400-e29b-4000-a000-000000000000',
      role: 'user',
      content: 'Hello',
      status: 'complete',
      timestamp: '2026-02-17T10:30:00Z',
    };
    expect(isValidMessage(message)).toBe(true);
  });

  test('isValidMessage should reject invalid messages', () => {
    expect(isValidMessage({ role: 'user' })).toBe(false); // Missing required fields
    expect(isValidMessage({ role: 'invalid', content: 'test', status: 'complete', timestamp: '2026-02-17T10:30:00Z' })).toBe(false); // Invalid role
  });

  // Source validation
  test('isValidSource should validate correct sources', () => {
    const source = { name: 'Test Document' };
    expect(isValidSource(source)).toBe(true);
  });

  // Error state validation
  test('isValidErrorState should validate correct error states', () => {
    const error = {
      type: 'network_error',
      message: 'Connection failed',
    };
    expect(isValidErrorState(error)).toBe(true);
  });

  test('isValidErrorState should reject invalid error states', () => {
    expect(isValidErrorState({ type: 'unknown_type', message: 'test' })).toBe(false);
    expect(isValidErrorState({ type: 'network_error' })).toBe(false); // Missing message
  });
});
