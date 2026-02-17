import { isValidChatSession } from './validation.js';

/**
 * Load session from localStorage
 */
export function loadSession() {
  try {
    const json = window.localStorage.getItem('courseflow_session');
    if (!json) return null;

    const session = JSON.parse(json);
    if (!isValidChatSession(session)) {
      console.warn('Invalid session schema in localStorage');
      return null;
    }
    return session;
  } catch (error) {
    console.error('Error loading session from localStorage:', error);
    return null;
  }
}

/**
 * Save session to localStorage
 */
export function saveSession(session) {
  try {
    if (!isValidChatSession(session)) {
      console.warn('Invalid session schema, not persisting');
      return false;
    }
    window.localStorage.setItem('courseflow_session', JSON.stringify(session));
    return true;
  } catch (error) {
    if (error.name === 'QuotaExceededError') {
      console.warn('localStorage quota exceeded, session not persisted');
      return false;
    }
    console.error('Error saving session to localStorage:', error);
    return false;
  }
}

/**
 * Clear session from localStorage
 */
export function clearSession() {
  try {
    window.localStorage.removeItem('courseflow_session');
    return true;
  } catch (error) {
    console.error('Error clearing session from localStorage:', error);
    return false;
  }
}
