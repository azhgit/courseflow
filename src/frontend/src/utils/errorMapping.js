/**
 * Error mapping from HTTP responses to user-facing error types
 */

export function mapHttpErrorToErrorState(status, body) {
  if (status === 429) {
    // Distinguish between hourly and daily quota limits
    if (body?.error === 'daily_quota_exhausted') {
      return {
        type: 'daily_quota',
        message: 'Daily demo limit reached. Resets at midnight.',
      };
    }
    return {
      type: 'ip_limit',
      message: 'Demo limit reached. Try again in 1 hour.',
      retry_after: 3600,
    };
  }

  if (status === 503) {
    return {
      type: 'network_error',
      message: 'Service unavailable. Try again later.',
    };
  }

  if (status >= 500) {
    return {
      type: 'network_error',
      message: 'Server error. Please try again.',
    };
  }

  return {
    type: 'network_error',
    message: 'Connection error. Please check your network and try again.',
  };
}

/**
 * Map SSE stream error events to error states
 */
export function mapSSEErrorToErrorState(errorType, message, errorSource = null) {
  if (errorType === 'no_relevant_documents') {
    return {
      type: 'no_documents',
      message: 'No content found for this query. Try rephrasing your question.',
    };
  }

  if (errorType === 'rate_limit_exceeded') {
    const sourceLabel = errorSource === 'local_guard' ? 'Local guard' : 'Gemini';
    return {
      type: 'rate_limit',
      source: errorSource || 'gemini',
      message: `${sourceLabel} rate limit reached. ${message || 'Please retry later.'}`,
    };
  }

  return {
    type: 'network_error',
    message: message || 'Connection lost. Please try again.',
  };
}
