import { makeRequest } from './client.js';
import { EXAMPLE_QUESTIONS } from '../constants/exampleQuestions.js';

/**
 * Post a question to the backend and return an SSE stream
 */
export async function postQuery(question, conversationId = null) {
  const body = {
    query: question,
    ...(conversationId && { conversation_id: conversationId }),
  };

  const response = await makeRequest('/api/v1/query/stream', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const error = new Error(`Query failed: ${response.status}`);
    error.status = response.status;
    error.body = errorBody;
    throw error;
  }

  return response;
}

/**
 * Fetch example questions from backend if available.
 * Falls back to local defaults when endpoint is missing.
 */
export async function getExampleQuestions() {
  try {
    const response = await makeRequest('/api/v1/demo/examples', {
      method: 'GET',
    });

    if (!response.ok) {
      return EXAMPLE_QUESTIONS;
    }

    const data = await response.json();
    return Array.isArray(data?.examples) && data.examples.length > 0
      ? data.examples
      : EXAMPLE_QUESTIONS;
  } catch {
    return EXAMPLE_QUESTIONS;
  }
}
