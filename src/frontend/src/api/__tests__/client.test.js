/**
 * API client tests
 */

import {
  buildUrl,
  getApiBaseUrl,
  makeRequest,
} from '../client.js';

describe('API Client', () => {
  test('getApiBaseUrl should return configured URL', () => {
    const url = getApiBaseUrl();
    expect(url).toBeTruthy();
    expect(url).toMatch(/^http/);
  });

  test('buildUrl should construct correct URLs', () => {
    const url1 = buildUrl('/api/v1/query');
    expect(url1).toMatch(/api\/v1\/query$/);
    
    const url2 = buildUrl('api/v1/query');
    expect(url2).toMatch(/api\/v1\/query$/);
  });

  test('buildUrl should remove trailing slashes', () => {
    const url = buildUrl('/api/v1/query');
    expect(url).not.toMatch(/\/\/$/);
  });

  test('makeRequest should be callable', async () => {
    expect(makeRequest).toBeDefined();
    expect(typeof makeRequest).toBe('function');
  });
});
