#!/usr/bin/env python3
"""
Quick test to verify all imports work correctly after refactoring.
Run this to check for import errors before running export_data.py
"""

import sys

def test_imports():
    """Test all module imports."""
    errors = []
    
    print("Testing imports...")
    
    try:
        print("  ✓ backend.config")
        from backend.config import (
            ROOT_DIR, DATA_DIR, MODELS_DIR, OUTPUT_DIR,
            DEFAULT_DATA_PATHS, CANCER_KEYWORDS, ICD10_CANCER_MAPPING,
            LAB_REFERENCE_RANGES, LAB_EXTRACTION_PATTERNS, ML_LAB_COLUMNS
        )
    except Exception as e:
        errors.append(f"backend.config: {e}")
    
    try:
        print("  ✓ backend.exceptions")
        from backend.exceptions import (
            SpectraError, DataError, DatasetNotFoundError,
            KnowledgeBaseError, ChromaDBError, LLMError
        )
    except Exception as e:
        errors.append(f"backend.exceptions: {e}")
    
    try:
        print("  ✓ backend.utils")
        from backend.utils import (
            extract_cancer_type, extract_icd10_codes, extract_drugs,
            extract_labs_from_text, flag_abnormal_labs, clean_string_column,
            calculate_risk_score
        )
    except Exception as e:
        errors.append(f"backend.utils: {e}")
    
    try:
        print("  ✓ backend.models")
        from backend.models import (
            ICD10Request, ICD10Response, TreatmentRequest, TreatmentResponse,
            AnalyzeSummaryRequest, AnalyzeSummaryResponse,
            AnalyzeRiskRequest, AnalyzeRiskResponse
        )
    except Exception as e:
        errors.append(f"backend.models: {e}")
    
    try:
        print("  ✓ backend.data_processor")
        from backend.data_processor import (
            load_dataset, process_patient, create_training_pairs,
            create_icd10_knowledge_base, load_and_process
        )
    except Exception as e:
        errors.append(f"backend.data_processor: {e}")
    
    try:
        print("  ✓ backend.rag_engine")
        from backend.rag_engine import (
            get_treatment_recommendation, analyze_patient_summary,
            analyze_risk_assessment, index_patient_data, check_rag_system
        )
    except Exception as e:
        errors.append(f"backend.rag_engine: {e}")
    
    try:
        print("  ✓ backend.export_data")
        from backend.export_data import main as export_main
    except Exception as e:
        errors.append(f"backend.export_data: {e}")
    
    if errors:
        print("\n❌ Import errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ All imports successful!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
