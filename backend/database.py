"""Database models and connection management for SPECTRA."""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Enum, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool
from datetime import datetime
import os

from backend.config_production import settings

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum('admin', 'doctor', 'nurse', 'staff'), default='doctor')
    department = Column(String(50), default='Genel')
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_patients = relationship("Patient", back_populates="creator")
    records = relationship("PatientRecord", back_populates="creator")

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(String(20), unique=True, nullable=False, index=True)
    tc_kimlik = Column(String(11), unique=True, nullable=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(Enum('E', 'K'), nullable=True)
    blood_type = Column(String(5), nullable=True)
    phone = Column(String(15), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(15), nullable=True)
    allergies = Column(Text, nullable=True)
    chronic_diseases = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", back_populates="created_patients")
    records = relationship("PatientRecord", back_populates="patient", cascade="all, delete-orphan")

class PatientRecord(Base):
    __tablename__ = "patient_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    record_type = Column(Enum('examination', 'lab', 'imaging', 'prescription', 'spectra'), default='examination')
    clinical_notes = Column(Text, nullable=True)
    lab_results = Column(Text, nullable=True)
    spectra_analysis = Column(JSON, nullable=True)
    icd10_codes = Column(JSON, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment_plan = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="records")
    creator = relationship("User", back_populates="records")

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    success = Column(Boolean, default=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)

# Database connection with production settings
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
