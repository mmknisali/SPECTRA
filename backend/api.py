"""
SPECTRA FastAPI Backend
=======================
Provides endpoints for ICD-10 coding, treatment recommendations,
patient summary extraction, and risk assessment.

Endpoints:
    GET  /                  — Frontend popup UI
    GET  /api               — API information
    GET  /health            — System status
    POST /predict/icd10     — ICD-10 code prediction
    POST /recommend/treatment — Treatment recommendation
    POST /analyze/summary   — Patient summary extraction
    POST /analyze/risk      — Risk assessment
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config import ALLOWED_ORIGINS, DATA_DIR, ROOT_DIR
from backend.models import (
    APIInfoResponse,
    AnalyzeRiskRequest,
    AnalyzeRiskResponse,
    AnalyzeSummaryRequest,
    AnalyzeSummaryResponse,
    HealthResponse,
    ICD10Code,
    ICD10Request,
    ICD10Response,
    TreatmentRequest,
    TreatmentResponse,
)
from backend.rag_engine import (
    analyze_patient_summary,
    analyze_risk_assessment,
    check_rag_system,
    get_treatment_recommendation,
)
from backend.routes.auth import router as auth_router
from backend.routes.patients import router as patients_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("spectra")

# ---------------------------------------------------------------------------
# Knowledge base (loaded at startup)
# ---------------------------------------------------------------------------
knowledge_base: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown handler."""
    global knowledge_base
    logger.info("Starting SPECTRA API...")

    # Load knowledge base
    try:
        kb_path = DATA_DIR / "knowledge_base.json"
        with open(kb_path, encoding="utf-8") as fh:
            knowledge_base = json.load(fh)
        logger.info("Knowledge base loaded: %d ICD-10 codes", len(knowledge_base))
    except FileNotFoundError:
        logger.warning("Knowledge base not found — run export_data.py first")

    # Check ChromaDB
    rag_status = check_rag_system()
    logger.info(
        "ChromaDB status: %s (%d documents)",
        rag_status.get("ready", False),
        rag_status.get("document_count", 0),
    )

    yield

    logger.info("Shutting down SPECTRA API...")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SPECTRA API",
    description="Oncology Assistant API — ICD-10 Coding, Patient Summary & Risk Assessment",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(patients_router)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_ollama() -> Dict[str, Any]:
    """Check if Ollama is accessible."""
    from backend.config import OLLAMA_HOST

    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {
                "available": True,
                "models": len(models),
                "model_names": [m.get("name") for m in models[:3]],
            }
        return {"available": False, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"available": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Serve the SPECTRA popup frontend."""
    html_path = ROOT_DIR / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return {"message": "SPECTRA API — Oncology Assistant (frontend not found)"}


@app.get("/api", response_model=APIInfoResponse)
async def api_info():
    """Return API information."""
    return APIInfoResponse(
        name="SPECTRA API",
        version="1.1.0",
        description="Oncology Assistant — ICD-10 Coding, Patient Summary & Risk Assessment",
        endpoints={
            "GET /": "Frontend popup UI",
            "GET /api": "API information",
            "GET /health": "System status",
            "POST /predict/icd10": "ICD-10 code prediction",
            "POST /recommend/treatment": "Treatment recommendation",
            "POST /analyze/summary": "Patient summary extraction",
            "POST /analyze/risk": "Risk assessment",
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Return system health status."""
    rag_status = check_rag_system()
    ollama_status = _check_ollama()

    return HealthResponse(
        status="healthy",
        knowledge_base_loaded=len(knowledge_base) > 0,
        knowledge_base_size=len(knowledge_base),
        chroma_ready=rag_status.get("ready", False),
        chroma_documents=rag_status.get("document_count", 0),
        ollama_available=ollama_status.get("available", False),
        ollama_models=ollama_status.get("models", 0),
    )


@app.post("/predict/icd10", response_model=ICD10Response)
async def predict_icd10(request: ICD10Request):
    """Suggest ICD-10 codes from clinical notes."""
    if not knowledge_base:
        logger.error("Knowledge base not loaded")
        raise HTTPException(status_code=503, detail="Knowledge base not loaded")

    try:
        logger.info("ICD-10 request for cancer_type: %s", request.cancer_type)

        suggested: List[ICD10Code] = []
        search_terms = request.clinical_note.lower()
        if request.cancer_type:
            search_terms += " " + request.cancer_type.lower()

        for kb_entry in knowledge_base:
            code = kb_entry["code"]
            cancer_types = kb_entry.get("cancer_types", [])
            desc = kb_entry.get("description", "").lower()

            score = 0.0
            if request.cancer_type and request.cancer_type in cancer_types:
                score += 0.5

            if any(term in desc for term in search_terms.split()[:5]):
                score += 0.3

            if code[:3] in search_terms.upper():
                score += 0.5

            if score > 0:
                suggested.append(ICD10Code(
                    code=code,
                    description=kb_entry.get("description", ""),
                    score=score,
                    cancer_types=cancer_types,
                ))

        suggested.sort(key=lambda x: x.score, reverse=True)
        logger.info("ICD-10 found %d codes", len(suggested))

        return ICD10Response(suggested_codes=suggested[:10], source="knowledge_base")

    except Exception as e:
        logger.error("ICD-10 prediction failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"ICD-10 prediction failed: {e}")


@app.post("/recommend/treatment", response_model=TreatmentResponse)
async def recommend_treatment(request: TreatmentRequest):
    """Recommend treatment options using RAG + LLM."""
    try:
        logger.info("Treatment recommendation for: %s", request.cancer_type)

        patient_labs = None
        if request.patient_labs:
            patient_labs = request.patient_labs.model_dump(exclude_none=True)

        recommendation = get_treatment_recommendation(
            cancer_type=request.cancer_type,
            patient_labs=patient_labs,
        )

        logger.info("Treatment recommendation source: %s", recommendation.get("source"))

        return TreatmentResponse(
            cancer_type=recommendation.get("cancer_type", request.cancer_type),
            recommended_labs=recommendation.get("recommended_labs", []),
            treatment_protocol=recommendation.get("treatment_protocol", ""),
            source=recommendation.get("source", "rag+llm"),
        )

    except Exception as e:
        logger.error("Treatment recommendation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Treatment recommendation failed: {e}")


@app.post("/analyze/summary", response_model=AnalyzeSummaryResponse)
async def analyze_summary(request: AnalyzeSummaryRequest):
    """Extract structured patient summary from clinical text."""
    try:
        logger.info("Analyze summary request (%d chars)", len(request.clinical_text))
        result = analyze_patient_summary(
            clinical_text=request.clinical_text,
            lab_text=request.lab_text or "",
        )

        return AnalyzeSummaryResponse(
            cancer_type=result.get("cancer_type", "Belirlenemedi"),
            stage=result.get("stage", "Belirtilmemiş"),
            treatment_history=result.get("treatment_history", []),
            current_medications=result.get("current_medications", []),
            key_findings=result.get("key_findings", []),
            performance_status=result.get("performance_status", "Belirtilmemiş"),
            source=result.get("source", "fallback"),
        )

    except Exception as e:
        logger.error("Summary analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summary analysis failed: {e}")


@app.post("/analyze/risk", response_model=AnalyzeRiskResponse)
async def analyze_risk(request: AnalyzeRiskRequest):
    """Generate risk assessment from clinical text."""
    try:
        logger.info("Analyze risk request (%d chars)", len(request.clinical_text))
        result = analyze_risk_assessment(
            clinical_text=request.clinical_text,
            lab_text=request.lab_text or "",
        )

        return AnalyzeRiskResponse(
            risk_level=result.get("risk_level", "düşük"),
            risk_factors=result.get("risk_factors", []),
            abnormal_labs=result.get("abnormal_labs", []),
            metastasis_indicators=result.get("metastasis_indicators", []),
            recommendations=result.get("recommendations", []),
            source=result.get("source", "fallback"),
        )

    except Exception as e:
        logger.error("Risk analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
