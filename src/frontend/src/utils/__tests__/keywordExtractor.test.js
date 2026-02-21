import { describe, it, expect } from 'vitest';
import { extractKeywords } from '../keywordExtractor';

describe('extractKeywords', () => {
  it('should extract meaningful keywords from a query', () => {
    const result = extractKeywords('What is photosynthesis?');
    expect(result).toContain('photosynthesis');
  });

  it('should remove stop words (the, is, a, an, etc)', () => {
    const result = extractKeywords('the is a an what how');
    expect(result).toEqual([]);
  });

  it('should filter out words shorter than 4 characters', () => {
    const result = extractKeywords('what ab go python');
    expect(result).not.toContain('ab');
    expect(result).not.toContain('go');
    expect(result).toContain('python');
  });

  it('should be case-insensitive', () => {
    const result1 = extractKeywords('Python Machine Learning');
    const result2 = extractKeywords('python machine learning');
    expect(result1).toEqual(result2);
  });

  it('should remove punctuation from word edges', () => {
    const result = extractKeywords('What is "photosynthesis"? It\'s amazing!');
    expect(result).toContain('photosynthesis');
    expect(result).toContain('amazing');
  });

  it('should limit to max_keywords (default 5)', () => {
    const result = extractKeywords('python javascript typescript golang rust kotlin scala clojure');
    expect(result.length).toBeLessThanOrEqual(5);
  });

  it('should respect custom max_keywords', () => {
    const result = extractKeywords('python javascript typescript golang rust clojure scheme', 3);
    expect(result.length).toBeLessThanOrEqual(3);
    expect(result.length).toBe(3);
  });

  it('should return unique keywords only', () => {
    const result = extractKeywords('python python python javascript javascript typescript');
    expect(result).toContain('python');
    expect(result).toContain('javascript');
    // Ensure no duplicates
    expect(new Set(result).size).toBe(result.length);
  });

  it('should handle empty input', () => {
    const result = extractKeywords('');
    expect(result).toEqual([]);
  });

  it('should handle only stop words', () => {
    const result = extractKeywords('the and or is but');
    expect(result).toEqual([]);
  });

  it('should work with longer queries', () => {
    const result = extractKeywords('How does machine learning work in computer vision applications?');
    expect(result).toContain('machine');
    expect(result).toContain('learning');
    expect(result).toContain('computer');
    expect(result).toContain('vision');
  });
});
