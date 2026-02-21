/**
 * Keyword extraction utilities for highlighting in source documents.
 */

/**
 * Extract meaningful keywords from a search query.
 *
 * Removes common stop words and filters by word length.
 * Returns up to maxKeywords words.
 *
 * @param {string} query - User search query string
 * @param {number} maxKeywords - Maximum number of keywords to return (default: 5)
 * @returns {string[]} List of extracted keywords (lowercase, unique)
 *
 * @example
 * extractKeywords("What is photosynthesis?")
 * // => ["photosynthesis"]
 *
 * @example
 * extractKeywords("How does machine learning work?")
 * // => ["machine", "learning", "work"]
 */
export function extractKeywords(query, maxKeywords = 5) {
  // Common English stop words
  const stopWords = new Set([
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'but', 'by',
    'for', 'from', 'had', 'has', 'have', 'he', 'her', 'his', 'how',
    'i', 'if', 'in', 'is', 'it', 'its', 'just', 'me', 'my', 'of',
    'on', 'or', 'our', 'out', 'over', 'she', 'so', 'than', 'that',
    'the', 'their', 'them', 'then', 'there', 'these', 'they', 'this',
    'to', 'too', 'under', 'up', 'very', 'was', 'we', 'what', 'when',
    'where', 'which', 'who', 'why', 'will', 'with', 'you', 'your',
    'can', 'could', 'would', 'should', 'do', 'does', 'did', 'wont',
    'dont', 'isnt', 'cant', 'shouldnt'
  ]);

  // Split and normalize
  const words = query.toLowerCase().split(/\s+/);

  // Filter: remove stop words, short words, keep unique
  const keywords = [];
  const seen = new Set();

  for (const word of words) {
    // Remove punctuation from edges
    const cleanWord = word.replace(/^[.,!?;:"'\[\]]+|[.,!?;:"'\[\]]+$/g, '');

    // Apply filters
    if (
      cleanWord &&
      cleanWord.length > 3 && // Minimum 4 characters
      !stopWords.has(cleanWord) &&
      !seen.has(cleanWord)
    ) {
      keywords.push(cleanWord);
      seen.add(cleanWord);

      // Stop if we've reached the limit
      if (keywords.length >= maxKeywords) {
        break;
      }
    }
  }

  return keywords;
}
