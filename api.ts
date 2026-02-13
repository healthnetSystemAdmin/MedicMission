import { Patient, OCRResponse } from './types.ts';

// Dynamically determine the backend host based on the current window location
// This ensures that whether accessed via localhost or a network IP, the frontend
// points to the correct backend instance on port 8000.
const getBaseUrl = () => {
  const hostname = window.location.hostname || 'localhost';
  const protocol = window.location.protocol;
  // Standard backend port for this app is 8000
  return `${protocol}//${hostname}:8000/api`;
};

const BASE_URL = getBaseUrl();

export const api = {
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${BASE_URL}/health`, { 
        method: 'GET',
        mode: 'cors',
        signal: AbortSignal.timeout(3000) 
      });
      return response.ok;
    } catch (e) {
      console.error("Health check failed:", e);
      return false;
    }
  },

  async captureAndOCR(imageBlob: Blob): Promise<OCRResponse> {
    const formData = new FormData();
    formData.append('file', imageBlob, 'capture.jpg');
    
    try {
      const response = await fetch(`${BASE_URL}/camera/capture-ocr`, {
        method: 'POST',
        body: formData,
        mode: 'cors',
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown server error' }));
        throw new Error(errorData.detail || `OCR Server Error (${response.status})`);
      }
      return response.json();
    } catch (error) {
      if (error instanceof Error && error.message.includes('fetch')) {
        throw new Error(`Connection to backend failed at ${BASE_URL}. Ensure backend is running.`);
      }
      throw error;
    }
  },

  async savePatient(patient: Patient): Promise<Patient> {
    try {
      const response = await fetch(`${BASE_URL}/patients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patient),
        mode: 'cors',
      });
      
      if (!response.ok) throw new Error(`Failed to save patient: ${response.statusText}`);
      return response.json();
    } catch (error) {
      console.error("Save error:", error);
      throw error;
    }
  },

  async getPatients(): Promise<Patient[]> {
    try {
      const response = await fetch(`${BASE_URL}/patients`, { mode: 'cors' });
      if (!response.ok) throw new Error('Failed to fetch patients');
      return response.json();
    } catch (error) {
      console.error("Fetch patients error:", error);
      throw error;
    }
  },

  async getPatient(id: number): Promise<Patient> {
    try {
      const response = await fetch(`${BASE_URL}/patients/${id}`, { mode: 'cors' });
      if (!response.ok) throw new Error('Patient not found');
      return response.json();
    } catch (error) {
      console.error("Fetch patient error:", error);
      throw error;
    }
  },

  getImageUrl(filename: string): string {
    return `${BASE_URL}/images/${filename}`;
  }
};
