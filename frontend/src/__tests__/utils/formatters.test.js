import { describe, it, expect } from 'vitest';
import { formatDate, formatFileSize, truncateText } from '../../utils/formatters';

describe('formatters', () => {
  describe('formatDate', () => {
    it('should format a valid date', () => {
      const date = new Date('2024-01-15T10:30:00Z');
      const formatted = formatDate(date);
      expect(formatted).toBeTruthy();
      expect(typeof formatted).toBe('string');
    });

    it('should handle invalid dates gracefully', () => {
      const result = formatDate(null);
      expect(result).toBe('-');
    });
  });

  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 B');
      expect(formatFileSize(1024)).toBe('1 KB');
      expect(formatFileSize(1048576)).toBe('1 MB');
      expect(formatFileSize(1073741824)).toBe('1 GB');
    });

    it('should handle invalid input', () => {
      expect(formatFileSize(null)).toBe('-');
      expect(formatFileSize(undefined)).toBe('-');
    });
  });

  describe('truncateText', () => {
    it('should truncate long text', () => {
      const longText = 'a'.repeat(100);
      const truncated = truncateText(longText, 50);
      expect(truncated.length).toBeLessThanOrEqual(53); // 50 + '...'
    });

    it('should not truncate short text', () => {
      const shortText = 'Short text';
      const result = truncateText(shortText, 50);
      expect(result).toBe(shortText);
    });

    it('should handle empty string', () => {
      expect(truncateText('', 50)).toBe('');
    });
  });
});

