
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class OCRField(BaseModel):
    value: str
    confidence: float

class OCRResponse(BaseModel):
    fields: Dict[str, OCRField]
    image: Dict[str, str]
    debug: Dict[str, str]

class PatientBase(BaseModel):
    philhealth_no: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = ""
    birth_date: Optional[str] = ""
    sex: Optional[str] = ""
    address: Optional[str] = ""
    contact_no: Optional[str] = ""
    id_image_path: str

class PatientCreate(PatientBase):
    ocr_raw_json: Optional[str] = None

class Patient(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
