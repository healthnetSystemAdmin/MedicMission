import os
import uuid
import threading
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import shutil

# Local imports
from database import engine, get_db, Base
import models
import schemas
from ocr.engine import OCRProcessor

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedicMission API")

# Setup Folders
DATA_DIR = "./data"
IMAGES_DIR = os.path.join(DATA_DIR, "id_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# CORS - Explicitly open for development and local network usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OCR Instance (lazy singleton)
ocr_engine = None
ocr_engine_lock = threading.Lock()


def get_ocr_engine() -> OCRProcessor:
    global ocr_engine
    if ocr_engine is None:
        with ocr_engine_lock:
            if ocr_engine is None:
                ocr_engine = OCRProcessor()
    return ocr_engine

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "engine": "paddleocr",
        "ocr_initialized": ocr_engine is not None,
        "db": "connected",
    }

@app.post("/api/camera/capture-ocr", response_model=schemas.OCRResponse)
async def capture_ocr(file: UploadFile = File(...)):
    # 1. Save File Temporarily
    filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(IMAGES_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Run OCR
        ocr = get_ocr_engine()
        ocr_result = ocr.process_image(file_path)
        return ocr_result
    except RuntimeError as e:
        print(f"OCR Runtime Error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"OCR Unavailable: {str(e)}")
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR Processing Failed: {str(e)}")

@app.post("/api/patients", response_model=schemas.Patient)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/api/patients", response_model=List[schemas.Patient])
def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    patients = db.query(models.Patient).order_by(models.Patient.created_at.desc()).offset(skip).limit(limit).all()
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
    # 0.0.0.0 is crucial for Raspberry Pi network access
    uvicorn.run(app, host="0.0.0.0", port=8000)
