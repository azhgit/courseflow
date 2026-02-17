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

/**
 * Fetch example questions from the backend demo cache
 */
export async function getExampleQuestions() {
  try {
    const response = await makeRequest('/api/v1/demo/examples', {
      method: 'GET',
    });

    if (!response.ok) {
      console.warn(`Failed to fetch example questions: ${response.status}`);
      return null;
    }

    const data = await response.json();
    return data.examples || null;
  } catch (error) {
    console.error('Error fetching example questions:', error);
    return null;
  }
}
