
export interface OCRField {
  value: string;
  confidence: number;
}

export interface OCRResponse {
  fields: {
    philhealth_no: OCRField;
    last_name: OCRField;
    first_name: OCRField;
    middle_name: OCRField;
    birth_date: OCRField;
    sex: OCRField;
    address: OCRField;
  };
  image: {
    stored_filename: string;
    preview_url: string;
  };
  debug: {
    ocr_engine: string;
    notes: string;
  };
}

export interface Patient {
  id?: number;
  created_at?: string;
  philhealth_no: string;
  last_name: string;
  first_name: string;
  middle_name: string;
  birth_date: string;
  sex: string;
  address: string;
  contact_no: string;
  id_image_path: string;
  ocr_raw_json?: string;
}

export enum CameraStatus {
  READY = 'READY',
  ON = 'CAMERA ON',
  PROCESSING = 'PROCESSING...',
}
