
import os
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import shutil

# Local imports
from .database import engine, get_db, Base
from . import models, schemas
from .ocr.engine import OCRProcessor

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedicMission API")

# Setup Folders
DATA_DIR = "./data"
IMAGES_DIR = os.path.join(DATA_DIR, "id_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OCR Instance (Singleton style)
ocr_engine = OCRProcessor()

@app.post("/api/camera/capture-ocr", response_model=schemas.OCRResponse)
async def capture_ocr(file: UploadFile = File(...)):
    # 1. Save File Temporarily
    filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(IMAGES_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Run OCR
    try:
        ocr_result = ocr_engine.process_image(file_path)
        return ocr_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patients", response_model=schemas.Patient)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/api/patients", response_model=List[schemas.Patient])
def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    patients = db.query(models.Patient).offset(skip).limit(limit).all()
    return patients

@app.get("/api/patients/{patient_id}", response_model=schemas.Patient)
def read_patient(patient_id: int, db: Session = Depends(get_db)):
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient

# Static access to images
app.mount("/api/images", StaticFiles(directory=IMAGES_DIR), name="images")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
