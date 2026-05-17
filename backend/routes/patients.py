"""Patient History API Routes for SPECTRA."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from backend.patient_history import get_history_manager
from backend.auth import get_current_user
from backend.database import User

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/search")
async def search_patients(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Search patients by ID or partial match."""
    manager = get_history_manager()
    results = manager.search_patients(q, limit)
    return {
        "success": True,
        "query": q,
        "count": len(results),
        "patients": results
    }

@router.get("/{patient_id}/history")
async def get_patient_history(
    patient_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get complete patient history and timeline."""
    manager = get_history_manager()
    history = manager.get_patient_history(patient_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Hasta bulunamadı")
    
    return {
        "success": True,
        "patient": {
            "id": history.patient_id,
            "gender": history.gender,
            "birth_date": history.birth_date,
            "age": history.age,
            "cancer_type": history.cancer_type,
            "stage": history.stage,
            "status": history.current_status
        },
        "timeline": history.get_timeline(),
        "treatments": history.get_treatment_summary(),
        "visit_count": len(history.visits)
    }

@router.get("/{patient_id}/recommendations")
async def get_patient_recommendations(
    patient_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get clinical recommendations based on patient history."""
    manager = get_history_manager()
    recommendations = manager.get_clinical_recommendations(patient_id)
    
    if "error" in recommendations:
        raise HTTPException(status_code=404, detail=recommendations["error"])
    
    return recommendations

@router.get("/{patient_id}/timeline")
async def get_patient_timeline(
    patient_id: str,
    limit: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get patient timeline (chronological events)."""
    manager = get_history_manager()
    history = manager.get_patient_history(patient_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Hasta bulunamadı")
    
    timeline = history.get_timeline()
    if limit:
        timeline = timeline[-limit:]  # Get last N events
    
    return {
        "success": True,
        "patient_id": patient_id,
        "timeline": timeline,
        "total_events": len(timeline)
    }
