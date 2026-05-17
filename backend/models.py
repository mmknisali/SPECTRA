"""
SPECTRA Pydantic Models
=======================
Request/response schemas for all API endpoints.

Organized by domain:
- ICD-10 coding
- Treatment recommendations
- Patient summary analysis
- Risk assessment
- Health checks
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.config import MAX_CLINICAL_NOTE_LENGTH


# ===========================================================================
# ICD-10 Coding
# ===========================================================================

class ICD10Request(BaseModel):
    """Request for ICD-10 code prediction."""

    clinical_note: str = Field(
        ...,
        max_length=MAX_CLINICAL_NOTE_LENGTH,
        description="Clinical notes text",
    )
    cancer_type: Optional[str] = Field(
        None,
        description="Cancer type to filter results",
    )


class ICD10Code(BaseModel):
    """Single ICD-10 code result."""

    code: str = Field(..., description="ICD-10 code (e.g. 'C22.0')")
    description: str = Field(..., description="Code description")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    cancer_types: List[str] = Field(..., description="Associated cancer types")


class ICD10Response(BaseModel):
    """Response for ICD-10 code prediction."""

    suggested_codes: List[ICD10Code] = Field(
        ..., description="List of matching ICD-10 codes",
    )
    source: str = Field("knowledge_base", description="Source of the prediction")


# ===========================================================================
# Treatment Recommendations
# ===========================================================================

class TreatmentLabInput(BaseModel):
    """Lab values for treatment recommendation."""

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
    """Request for treatment recommendation."""

    cancer_type: str = Field(..., description="Target cancer type")
    patient_labs: Optional[TreatmentLabInput] = Field(
        None, description="Patient laboratory values",
    )


class TreatmentResponse(BaseModel):
    """Response for treatment recommendation."""

    cancer_type: str = Field(..., description="Echo of requested cancer type")
    recommended_labs: List[str] = Field(..., description="Recommended lab tests")
    treatment_protocol: str = Field(..., description="Detailed treatment protocol")
    source: str = Field("rag+llm", description="Source: 'rag+llm' or 'fallback'")


# ===========================================================================
# Patient Summary Analysis
# ===========================================================================

class AnalyzeSummaryRequest(BaseModel):
    """Request for patient summary extraction."""

    clinical_text: str = Field(
        ...,
        max_length=MAX_CLINICAL_NOTE_LENGTH,
        description="Clinical text to analyze",
    )
    lab_text: Optional[str] = Field(None, description="Optional lab results text")


class AnalyzeSummaryResponse(BaseModel):
    """Response for patient summary extraction."""

    cancer_type: str = Field(..., description="Identified cancer type")
    stage: str = Field(..., description="Cancer stage")
    treatment_history: List[str] = Field(..., description="Past treatments")
    current_medications: List[str] = Field(..., description="Current medications")
    key_findings: List[str] = Field(..., description="Key clinical findings")
    performance_status: str = Field(..., description="ECOG or performance status")
    source: str = Field(..., description="Source: 'rag+llm' or 'fallback'")


# ===========================================================================
# Risk Assessment
# ===========================================================================

class AnalyzeRiskRequest(BaseModel):
    """Request for risk assessment."""

    clinical_text: str = Field(
        ...,
        max_length=MAX_CLINICAL_NOTE_LENGTH,
        description="Clinical text to analyze",
    )
    lab_text: Optional[str] = Field(None, description="Optional lab results text")


class AnalyzeRiskResponse(BaseModel):
    """Response for risk assessment."""

    risk_level: str = Field(
        ...,
        pattern="^(düşük|orta|yüksek)$",
        description="Risk level",
    )
    risk_factors: List[str] = Field(..., description="Identified risk factors")
    abnormal_labs: List[str] = Field(..., description="Abnormal lab values")
    metastasis_indicators: List[str] = Field(..., description="Metastasis indicators")
    recommendations: List[str] = Field(..., description="Clinical recommendations")
    source: str = Field(..., description="Source: 'rag+llm' or 'fallback'")


# ===========================================================================
# Health Check
# ===========================================================================

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="System status: 'healthy' or 'degraded'")
    knowledge_base_loaded: bool
    knowledge_base_size: int
    chroma_ready: bool
    chroma_documents: int
    ollama_available: bool
    ollama_models: int


# ===========================================================================
# API Info
# ===========================================================================

class APIInfoResponse(BaseModel):
    """API information response."""

    name: str
    version: str
    description: str
    endpoints: Dict[str, str] = Field(
        ..., description="Map of endpoint paths to descriptions",
    )
