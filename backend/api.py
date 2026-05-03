"""
SPECTRA FastAPI Backend
Provides endpoints for cancer prediction, ICD-10 coding, and treatment recommendations
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import joblib
from pathlib import Path
import json
import pandas as pd
import os

# Configure CORS origins from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler (replaces @app.on_event)"""
    # Startup
    global classifier, scaler, label_encoder, knowledge_base

    try:
        classifier = joblib.load(MODEL_DIR / "cancer_classifier.joblib")
        scaler = joblib.load(MODEL_DIR / "feature_scaler.joblib")
        label_encoder = joblib.load(MODEL_DIR / "label_encoder.joblib")
        print("ML models loaded")
    except FileNotFoundError:
        print("ML models not found - run cancer_classifier.py first")

    try:
        with open(DATA_DIR / "knowledge_base.json", encoding='utf-8') as f:
            knowledge_base = json.load(f)
        print(f"Knowledge base loaded: {len(knowledge_base)} codes")
    except FileNotFoundError:
        print("Knowledge base not found - run export_data.py first")

    yield

    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="SPECTRA API",
    description="Oncology Assistant API - Cancer Prediction & ICD-10 Coding",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = Path(__file__).parent.parent / "models"
DATA_DIR = Path(__file__).parent.parent / "data"

# Load models at startup
classifier = None
scaler = None
label_encoder = None
knowledge_base = []


# Request/Response models
class PatientLabInput(BaseModel):
    hba1c: Optional[float] = None
    üre: Optional[float] = None
    kreatinin: Optional[float] = None
    bun: Optional[float] = None
    alt: Optional[float] = None
    alp: Optional[float] = None
    ast: Optional[float] = None
    ggt: Optional[float] = None
    bilirubin: Optional[float] = None
    potasyum: Optional[float] = None
    kalsiyum: Optional[float] = None
    magnezyum: Optional[float] = None
    klor: Optional[float] = None
    albumin: Optional[float] = None
    crp: Optional[float] = None
    ldh: Optional[float] = None
    sodyum: Optional[float] = None


class CancerPredictionResponse(BaseModel):
    cancer_type: str
    confidence: float
    all_predictions: Dict[str, float]


class ICD10Request(BaseModel):
    clinical_note: str
    cancer_type: Optional[str] = None


class ICD10Response(BaseModel):
    suggested_codes: List[Dict[str, Any]]
    source: str


class TreatmentRequest(BaseModel):
    cancer_type: str
    patient_labs: Optional[PatientLabInput] = None


class TreatmentResponse(BaseModel):
    cancer_type: str
    recommended_medications: List[str]
    recommended_labs: List[str]
    protocols: List[str]


@app.get("/")
async def root():
    return {"message": "SPECTRA API - Oncology Assistant"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "models_loaded": classifier is not None,
        "knowledge_base_size": len(knowledge_base)
    }


@app.post("/predict/cancer", response_model=CancerPredictionResponse)
async def predict_cancer(labs: PatientLabInput):
    """Predict cancer type from lab values"""
    if not classifier or not scaler or not label_encoder:
        raise HTTPException(status_code=503, detail="Models not loaded")

    lab_columns = [
        'hba1c', 'üre', 'kreatinin', 'bun', 'alt', 'alp', 'ast', 'ggt',
        'bilirubin', 'potasyum', 'kalsiyum', 'magnezyum', 'klor',
        'albumin', 'crp', 'ldh', 'sodyum'
    ]

    features = []
    for col in lab_columns:
        val = getattr(labs, col, None)
        features.append(float(val) if val is not None else 0.0)

    # Add engineered features (ratios) to match training
    # Uses index positions: ALT=4, AST=5, BUN=3, Creatinine=2
    ratios = []
    if features[5] > 0:  # ALT index
        ratios.append(features[4] / features[5])  # AST/ALT
    else:
        ratios.append(0)
    if features[3] > 0:  # BUN index
        ratios.append(features[2] / features[3])  # Creatinine/BUN
    else:
        ratios.append(0)

    features.extend(ratios)
    features = scaler.transform([features])

    pred = classifier.predict(features)[0]
    proba = classifier.predict_proba(features)[0]

    predictions = {
        label_encoder.classes_[i]: float(p)
        for i, p in enumerate(proba)
    }

    return CancerPredictionResponse(
        cancer_type=label_encoder.classes_[pred],
        confidence=float(max(proba)),
        all_predictions=predictions
    )


@app.post("/predict/icd10", response_model=ICD10Response)
async def predict_icd10(request: ICD10Request):
    """Suggest ICD-10 codes from clinical notes"""
    if not knowledge_base:
        raise HTTPException(status_code=503, detail="Knowledge base not loaded")

    suggested = []
    search_terms = request.clinical_note.lower()

    if request.cancer_type:
        search_terms += " " + request.cancer_type.lower()

    for kb_entry in knowledge_base:
        code = kb_entry['code']
        cancer_types = kb_entry.get('cancer_types', [])
        desc = kb_entry.get('description', '').lower()

        score = 0
        if request.cancer_type and request.cancer_type in cancer_types:
            score += 0.5

        if any(term in desc for term in search_terms.split()[:5]):
            score += 0.3

        if code[:3] in search_terms.upper():
            score += 0.5

        if score > 0:
            suggested.append({
                'code': code,
                'description': kb_entry.get('description', ''),
                'score': score,
                'cancer_types': cancer_types
            })

    suggested.sort(key=lambda x: x['score'], reverse=True)

    return ICD10Response(
        suggested_codes=suggested[:10],
        source="knowledge_base"
    )


@app.post("/recommend/treatment", response_model=TreatmentResponse)
async def recommend_treatment(request: TreatmentRequest):
    """Recommend treatment options"""
    treatment_mapping = {
        'Karaciğer kanseri': {
            'medications': ['Sorafenib', 'Levatinib', 'Atezolizumab', 'Bevacizumab'],
            'labs': ['AST', 'ALT', 'Bilirubin', 'AFP', 'Alp'],
            'protocols': ['Transarteriyel Kemoblokasyon', 'Radyoablasyon', 'Cerrahi rezeksiyon']
        },
        'Meme Kanseri': {
            'medications': ['Tamoksifen', 'Anastrozol', 'Letrozol', 'Trastuzumab'],
            'labs': ['CA-15.3', 'CEA', 'HER2', 'ER', 'PR'],
            'protocols': ['Mastektomi', 'Lumpektomi', 'Kemoterapi', 'Radyoterapi']
        },
        'Multipl miyelom': {
            'medications': ['Bortezomib', 'Lenalidomid', 'Dexametazon', 'Daratumumab'],
            'labs': ['Beta-2 mikroglobulin', 'Serbest zincir', 'M protein', 'Kreatinin'],
            'protocols': ['VTD protokolü', 'VRd protokolü', 'Otolog nakil']
        },
        'Over kanseri': {
            'medications': ['Karboplatin', 'Paklitaksel', 'Bevacizumab', 'Olaparib'],
            'labs': ['CA-125', 'HE4', 'AFP', 'CEA'],
            'protocols': ['Sitoredüktif cerrahi', 'Kemoterapi', 'PARP inhibitörleri']
        },
        'Prostat kanseri': {
            'medications': ['Abirateron', 'Enzalutamid', 'Docetaksel', 'Denosumab'],
            'labs': ['PSA', 'Fosfataz', 'Kreatinin', 'Hb'],
            'protocols': ['Radikal prostatektomi', 'Radyoterapi', 'ADT']
        }
    }

    treatment = treatment_mapping.get(
        request.cancer_type,
        treatment_mapping['Karaciğer kanseri']
    )

    return TreatmentResponse(
        cancer_type=request.cancer_type,
        recommended_medications=treatment['medications'],
        recommended_labs=treatment['labs'],
        protocols=treatment['protocols']
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)