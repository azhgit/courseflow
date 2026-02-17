import { makeRequest } from './client.js';

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

const DEFAULT_EXAMPLES = [
  'What is photosynthesis?',
  'How does machine learning work?',
  'What are the benefits of exercise?',
  'Explain the theory of relativity',
];

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
      return DEFAULT_EXAMPLES;
    }

    const data = await response.json();
    return Array.isArray(data?.examples) && data.examples.length > 0
      ? data.examples
      : DEFAULT_EXAMPLES;
  } catch {
    return DEFAULT_EXAMPLES;
  }
}
