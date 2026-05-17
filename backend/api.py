"""
SPECTRA FastAPI Backend
Provides endpoints for ICD-10 coding and treatment recommendations
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("spectra")

# Import RAG engine
from .rag_engine import (
    get_treatment_recommendation,
    check_rag_system,
    analyze_patient_summary,
    analyze_risk_assessment,
    index_patient_data
)

# Configure CORS - allow all for Cloudflare tunnel
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# Request size limits
MAX_CLINICAL_NOTE_LENGTH = 10000  # 10KB max for clinical notes

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler (replaces @app.on_event)"""
    # Startup
    global knowledge_base
    logger.info("Starting SPECTRA API...")

    try:
        with open(DATA_DIR / "knowledge_base.json", encoding='utf-8') as f:
            knowledge_base = json.load(f)
        logger.info(f"Knowledge base loaded: {len(knowledge_base)} ICD-10 codes")
    except FileNotFoundError:
        logger.warning("Knowledge base not found - run export_data.py first")

    # Check ChromaDB
    rag_status = check_rag_system()
    logger.info(f"ChromaDB status: {rag_status.get('ready', False)} ({rag_status.get('document_count', 0)} documents)")

    yield

    # Shutdown
    logger.info("Shutting down SPECTRA API...")


app = FastAPI(
    title="SPECTRA API",
    description="Oncology Assistant API - ICD-10 Coding & Treatment Recommendations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

# Knowledge base
knowledge_base = []


class ICD10Request(BaseModel):
    clinical_note: str = Field(..., max_length=MAX_CLINICAL_NOTE_LENGTH)
    cancer_type: Optional[str] = None


class ICD10Response(BaseModel):
    suggested_codes: List[Dict[str, Any]]
    source: str


class TreatmentLabInput(BaseModel):
    """Lab values for treatment recommendation"""
    hba1c: Optional[float] = None
    üre: Optional[float] = None
    kreatinin: Optional[float] = None
    bun: Optional[float] = None
    alt: Optional[float] = None
    alp: Optional[float] = None
    ast: Optional[float] = None
    ggt: Optional[float] = None
    bilirubin: Optional[float] = None
    crp: Optional[float] = None
    ldh: Optional[float] = None
    albumin: Optional[float] = None


class TreatmentRequest(BaseModel):
    cancer_type: str
    patient_labs: Optional[TreatmentLabInput] = None


class TreatmentResponse(BaseModel):
    cancer_type: str
    recommended_labs: List[str]
    treatment_protocol: str
    source: str = "rag+llm"


class AnalyzeSummaryRequest(BaseModel):
    clinical_text: str = Field(..., max_length=MAX_CLINICAL_NOTE_LENGTH)
    lab_text: Optional[str] = None


class AnalyzeSummaryResponse(BaseModel):
    cancer_type: str
    stage: str
    treatment_history: List[str]
    current_medications: List[str]
    key_findings: List[str]
    performance_status: str
    source: str


class AnalyzeRiskRequest(BaseModel):
    clinical_text: str = Field(..., max_length=MAX_CLINICAL_NOTE_LENGTH)
    lab_text: Optional[str] = None


class AnalyzeRiskResponse(BaseModel):
    risk_level: str
    risk_factors: List[str]
    abnormal_labs: List[str]
    metastasis_indicators: List[str]
    recommendations: List[str]
    source: str


@app.get("/")
async def root():
    """Serve the SPECTRA popup frontend"""
    html_path = ROOT_DIR / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return {"message": "SPECTRA API - Oncology Assistant (frontend not found)"}


@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "SPECTRA API",
        "version": "1.0.0",
        "description": "Oncology Assistant - ICD-10 Coding, Patient Summary & Risk Assessment",
        "endpoints": {
            "GET /": "Frontend popup UI",
            "GET /api": "API information",
            "GET /health": "System status",
            "POST /predict/icd10": "ICD-10 code prediction",
            "POST /recommend/treatment": "Treatment recommendation",
            "POST /analyze/summary": "Patient summary extraction",
            "POST /analyze/risk": "Risk assessment",
        }
    }


def check_ollama() -> dict:
    """Check if Ollama is accessible"""
    import requests
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        response = requests.get(f"{ollama_host}/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {"available": True, "models": len(models), "model_names": [m.get("name") for m in models[:3]]}
        return {"available": False, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/health")
async def health():
    # Check ChromaDB/RAG system status
    rag_status = check_rag_system()
    
    # Check Ollama
    ollama_status = check_ollama()

    return {
        "status": "healthy",
        "knowledge_base_loaded": len(knowledge_base) > 0,
        "knowledge_base_size": len(knowledge_base),
        "chroma_ready": rag_status.get("ready", False),
        "chroma_documents": rag_status.get("document_count", 0),
        "ollama_available": ollama_status.get("available", False),
        "ollama_models": ollama_status.get("models", 0)
    }


@app.post("/predict/icd10", response_model=ICD10Response)
async def predict_icd10(request: ICD10Request):
    """Suggest ICD-10 codes from clinical notes"""
    if not knowledge_base:
        logger.error("Knowledge base not loaded")
        raise HTTPException(status_code=503, detail="Knowledge base not loaded")

    try:
        logger.info(f"ICD-10 request for cancer_type: {request.cancer_type}")
        
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
        
        logger.info(f"ICD-10 found {len(suggested)} codes")
        
        return ICD10Response(
            suggested_codes=suggested[:10],
            source="knowledge_base"
        )
    except Exception as e:
        logger.error(f"ICD-10 prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ICD-10 prediction failed: {str(e)}")


@app.post("/recommend/treatment", response_model=TreatmentResponse)
async def recommend_treatment(request: TreatmentRequest):
    """Recommend treatment options using RAG + LLM"""
    try:
        logger.info(f"Treatment recommendation for: {request.cancer_type}")
        
        # Convert patient_labs to dict if provided
        patient_labs = None
        if request.patient_labs:
            patient_labs = request.patient_labs.model_dump(exclude_none=True)

        # Get treatment recommendation from RAG engine
        recommendation = get_treatment_recommendation(
            cancer_type=request.cancer_type,
            patient_labs=patient_labs
        )
        
        logger.info(f"Treatment recommendation source: {recommendation.get('source')}")

        return TreatmentResponse(
            cancer_type=recommendation.get('cancer_type', request.cancer_type),
            recommended_labs=recommendation.get('recommended_labs', []),
            treatment_protocol=recommendation.get('treatment_protocol', ''),
            source=recommendation.get('source', 'rag+llm')
        )
    except Exception as e:
        logger.error(f"Treatment recommendation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Treatment recommendation failed: {str(e)}")


@app.post("/analyze/summary", response_model=AnalyzeSummaryResponse)
async def analyze_summary(request: AnalyzeSummaryRequest):
    """Extract structured patient summary from clinical text"""
    try:
        logger.info(f"Analyze summary request ({len(request.clinical_text)} chars)")
        result = analyze_patient_summary(
            clinical_text=request.clinical_text,
            lab_text=request.lab_text or ""
        )

        return AnalyzeSummaryResponse(
            cancer_type=result.get("cancer_type", "Belirlenemedi"),
            stage=result.get("stage", "Belirtilmemiş"),
            treatment_history=result.get("treatment_history", []),
            current_medications=result.get("current_medications", []),
            key_findings=result.get("key_findings", []),
            performance_status=result.get("performance_status", "Belirtilmemiş"),
            source=result.get("source", "fallback")
        )
    except Exception as e:
        logger.error(f"Summary analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary analysis failed: {str(e)}")


@app.post("/analyze/risk", response_model=AnalyzeRiskResponse)
async def analyze_risk(request: AnalyzeRiskRequest):
    """Generate risk assessment from clinical text"""
    try:
        logger.info(f"Analyze risk request ({len(request.clinical_text)} chars)")
        result = analyze_risk_assessment(
            clinical_text=request.clinical_text,
            lab_text=request.lab_text or ""
        )

        return AnalyzeRiskResponse(
            risk_level=result.get("risk_level", "düşük"),
            risk_factors=result.get("risk_factors", []),
            abnormal_labs=result.get("abnormal_labs", []),
            metastasis_indicators=result.get("metastasis_indicators", []),
            recommendations=result.get("recommendations", []),
            source=result.get("source", "fallback")
        )
    except Exception as e:
        logger.error(f"Risk analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)