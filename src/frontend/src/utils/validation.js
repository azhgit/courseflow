/**
 * Validation functions for data model entities
 */

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ISO8601_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;

export function isValidUUID(value) {
  return typeof value === 'string' && UUID_PATTERN.test(value);
}

export function isValidISO8601(value) {
  return typeof value === 'string' && ISO8601_PATTERN.test(value);
}

export function isValidChatSession(obj) {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    isValidUUID(obj.conversation_id) &&
    Array.isArray(obj.messages) &&
    isValidISO8601(obj.created_at) &&
    isValidISO8601(obj.updated_at) &&
    obj.messages.every(isValidMessage)
  );
}

export function isValidMessage(obj) {
  const isValidStatus = ['in-progress', 'complete'].includes(obj?.status);
  const isValidContentLength = typeof obj?.content === 'string'
    && obj.content.length <= 10000
    && (
      (obj.status === 'in-progress' && obj.content.length >= 0)
      || (obj.status === 'complete' && obj.content.length > 0)
    );

  return (
    typeof obj === 'object' &&
    obj !== null &&
    isValidUUID(obj.id) &&
    ['user', 'assistant'].includes(obj.role) &&
    isValidStatus &&
    isValidContentLength &&
    isValidISO8601(obj.timestamp) &&
    (!obj.sources || (Array.isArray(obj.sources) && obj.sources.every(isValidSource)))
  );
}

export function isValidSource(obj) {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof obj.name === 'string' &&
    obj.name.length > 0 &&
    obj.name.length <= 200
  );
}

export function isValidErrorState(obj) {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    ['ip_limit', 'daily_quota', 'no_documents', 'network_error'].includes(obj.type) &&
    typeof obj.message === 'string' &&
    obj.message.length > 0
  );
}
