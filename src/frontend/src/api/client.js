/**
 * API client for CourseFlow backend
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function buildUrl(endpoint) {
  const base = getApiBaseUrl().replace(/\/$/, '');
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${path}`;
}

/**
 * Make a generic HTTP request
 */
export async function makeRequest(endpoint, options = {}) {
  const url = buildUrl(endpoint);
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  return response;
}

/**
 * Handle API error response
 */
export function handleApiError(response) {
  const error = new Error(`API Error: ${response.status}`);
  error.status = response.status;
  error.response = response;
  return error;
}
