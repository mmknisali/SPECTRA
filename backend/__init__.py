"""
SPECTRA Backend Package
=======================
Clinical decision support system for Turkish healthcare.

Modules:
    config            — Centralized configuration and constants
    exceptions        — Custom exception hierarchy
    utils             — Shared utility functions
    models            — Pydantic request/response schemas
    data_processor    — CSV/Excel loading, cleaning, training pair creation
    rag_engine        — ChromaDB + Ollama RAG pipeline with fallbacks
    api               — FastAPI application and routes
    export_data       — Data export pipeline orchestrator
    cancer_classifier — XGBoost cancer type classifier (optional)
"""

__version__ = "1.1.0"
