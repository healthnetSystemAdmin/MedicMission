
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    philhealth_no = Column(String, index=True)
    last_name = Column(String, index=True)
    first_name = Column(String)
    middle_name = Column(String)
    birth_date = Column(String)
    sex = Column(String)
    address = Column(Text)
    contact_no = Column(String)
    id_image_path = Column(String)
    ocr_raw_json = Column(Text, nullable=True)
