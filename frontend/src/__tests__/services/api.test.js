import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../../services/api';

// Mock fetch globally
global.fetch = vi.fn();

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('processRFP', () => {
    it('should upload and process RFP file', async () => {
      const mockResponse = {
        extracted_text: 'Sample extracted text',
        language: 'en',
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const result = await api.processRFP(file);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/process-rfp'),
        expect.objectContaining({
          method: 'POST',
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle API errors', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      const file = new File(['test'], 'test.pdf');
      
      await expect(api.processRFP(file)).rejects.toThrow();
    });
  });

  describe('runPreprocess', () => {
    it('should run preprocess agent', async () => {
      const mockResponse = {
        language: 'en',
        cleaned_text: 'Cleaned text',
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.runPreprocess('extracted text', {});

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/run-preprocess'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('runRequirements', () => {
    it('should extract requirements', async () => {
      const mockResponse = {
        solution_requirements: [],
        response_structure_requirements: [],
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const preprocessResult = {
        language: 'en',
        cleaned_text: 'Text',
      };

      const result = await api.runRequirements(preprocessResult, false);

      expect(result).toEqual(mockResponse);
    });
  });
});

