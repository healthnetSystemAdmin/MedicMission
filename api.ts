
import { Patient, OCRResponse } from './types';

// In a real RPi environment, this might be 'http://localhost:8000'
const BASE_URL = 'http://localhost:8000/api';

export const api = {
  async captureAndOCR(imageBlob: Blob): Promise<OCRResponse> {
    const formData = new FormData();
    formData.append('file', imageBlob, 'capture.jpg');
    
    const response = await fetch(`${BASE_URL}/camera/capture-ocr`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) throw new Error('OCR Failed');
    return response.json();
  },

  async savePatient(patient: Patient): Promise<Patient> {
    const response = await fetch(`${BASE_URL}/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patient),
    });
    
    if (!response.ok) throw new Error('Failed to save patient');
    return response.json();
  },

  async getPatients(): Promise<Patient[]> {
    const response = await fetch(`${BASE_URL}/patients`);
    if (!response.ok) throw new Error('Failed to fetch patients');
    return response.json();
  },

  async getPatient(id: number): Promise<Patient> {
    const response = await fetch(`${BASE_URL}/patients/${id}`);
    if (!response.ok) throw new Error('Patient not found');
    return response.json();
  },

  getImageUrl(filename: string): string {
    return `${BASE_URL}/images/${filename}`;
  }
};
