# Development Guide

## Environment Setup

### Option 1: direnv (Recommended)

```bash
direnv allow
```

This automatically:
- Activates the virtual environment
- Sets `PYTHONPATH="$PWD"`
- Shows a welcome banner with available commands

### Option 2: nix-shell

```bash
nix-shell
```

Creates a virtual environment if missing and installs dependencies.

### Option 3: devenv

```bash
devenv shell
```

### Option 4: Manual

```bash
python3 -m venv venv
source venv/bin/activate
export PYTHONPATH="$PWD"
pip install -r requirements.txt
```

## Project Structure

```
SPECTRA/
├── backend/
│   ├── __init__.py             # Package metadata (version)
│   ├── config.py               # Single source of truth for all constants
│   ├── exceptions.py           # Custom exception hierarchy
│   ├── utils.py                # Pure helper functions (no side effects)
│   ├── models.py               # Pydantic request/response schemas
│   ├── data_processor.py       # CSV/Excel loading, cleaning, training pairs
│   ├── rag_engine.py           # ChromaDB + Ollama RAG pipeline
│   ├── api.py                  # FastAPI application and routes
│   ├── export_data.py          # Data export pipeline orchestrator
│   └── cancer_classifier.py    # XGBoost model (optional)
├── docs/
│   ├── api.md                  # API reference
│   ├── development.md          # This file
│   └── deployment.md           # Deployment guide
├── index.html                  # Frontend popup (served at GET /)
├── requirements.txt            # Python dependencies
├── .envrc                      # direnv configuration
├── shell.nix                   # Nix shell configuration
├── devenv.nix                  # devenv configuration
├── AGENTS.md                   # Agent guide
└── README.md                   # Main documentation
```

## Module Responsibilities

### `config.py`
Centralizes all configuration:
- Project paths (`ROOT_DIR`, `DATA_DIR`, `MODELS_DIR`)
- Ollama settings (`OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`)
- API settings (`ALLOWED_ORIGINS`, `MAX_CLINICAL_NOTE_LENGTH`)
- Domain data (`CANCER_KEYWORDS`, `ICD10_CANCER_MAPPING`, `LAB_REFERENCE_RANGES`)

**To add a new cancer type:** Edit `CANCER_KEYWORDS` and optionally `ICD10_CANCER_MAPPING`, then re-run `export_data.py`.

### `utils.py`
Pure functions with no side effects:
- `extract_cancer_type(text)` — Keyword-based cancer extraction
- `extract_icd10_codes(string)` — Regex ICD-10 extraction
- `extract_drugs(string)` — Bracket-delimited drug extraction
- `extract_labs_from_text(text)` — Lab value parsing
- `flag_abnormal_labs(dict)` — Range checking
- `clean_string_column(value)` — String cleaning
- `truncate_text(text, max)` — Text truncation
- `calculate_risk_score(...)` — Risk level calculation

### `models.py`
Pydantic schemas organized by domain:
- ICD-10: `ICD10Request`, `ICD10Code`, `ICD10Response`
- Treatment: `TreatmentLabInput`, `TreatmentRequest`, `TreatmentResponse`
- Summary: `AnalyzeSummaryRequest`, `AnalyzeSummaryResponse`
- Risk: `AnalyzeRiskRequest`, `AnalyzeRiskResponse`
- Health: `HealthResponse`
- Info: `APIInfoResponse`

### `data_processor.py`
Data loading and processing pipeline:
1. `load_dataset()` — Read CSV or Excel with fallback paths
2. `extract_lab_values(row)` — Structured columns + text parsing
3. `process_patient(row)` — Full row → structured dict
4. `create_training_pairs(df)` — Q&A pairs for LoRA
5. `create_icd10_knowledge_base(df)` — ICD-10 → cancer_type map
6. `load_and_process()` — Orchestrates steps 1-5

### `rag_engine.py`
RAG pipeline with fallback:
- `get_chroma_client()` — ChromaDB client initialization
- `query_similar_patients(type)` — Search by cancer type
- `query_similar_patients_by_text(text)` — Search by clinical text
- `call_ollama_api(prompt)` — LLM API call
- `parse_llm_response(text)` — JSON parsing
- `build_treatment_prompt(...)` — Prompt construction
- `get_treatment_recommendation(type, labs)` — RAG + LLM treatment
- `get_fallback_recommendation(type)` — Rule-based treatment (5 types)
- `get_fallback_summary(text, labs)` — Rule-based summary
- `get_fallback_risk(text, labs)` — Rule-based risk assessment
- `analyze_patient_summary(text, labs)` — Summary with fallback
- `analyze_risk_assessment(text, labs)` — Risk with fallback
- `index_patient_data(df)` — ChromaDB bulk indexing
- `check_rag_system()` — Status check

### `api.py`
FastAPI application:
- Lifespan handler for startup/shutdown
- CORS middleware
- 7 endpoints (/, /api, /health, /predict/icd10, /recommend/treatment, /analyze/summary, /analyze/risk)
- Request validation via Pydantic models
- Error handling with HTTPException

### `export_data.py`
Pipeline orchestrator:
- `export_training_data(pairs)` → `data/training_data.json`
- `export_knowledge_base(kb)` → `data/knowledge_base.json`
- `export_cleaned_data(df)` → `data/cleaned_patients.csv`
- `index_chromadb(df)` → `data/chroma/`

## Data Flow

```
hackathon_veri.csv (365K rows)
    ↓
data_processor.py
    ├── extract_cancer_type() from epikriz/hikaye text
    ├── extract_lab_values() from columns + lab_sonuclari text
    ├── extract_drugs() from ilac brackets
    └── extract_icd10_codes() from icd10 column
    ↓
export_data.py
    ├── training_data.json (Q&A pairs)
    ├── knowledge_base.json (ICD-10 mappings)
    ├── cleaned_patients.csv (structured data)
    └── chroma/ (vector index)
    ↓
api.py (FastAPI)
    ├── /analyze/risk → rag_engine.py → Ollama or fallback
    ├── /analyze/summary → rag_engine.py → Ollama or fallback
    └── /predict/icd10 → knowledge_base.json scoring
```

## Code Conventions

### Python Style
- Follow PEP 8
- Use type hints for all function signatures
- Docstrings (Google style) for all public functions
- Maximum line length: 100 characters
- Import order: stdlib → third-party → local

### Example

```python
from typing import Optional
import re

from backend.config import CANCER_KEYWORDS


def extract_cancer_type(text: str) -> Optional[str]:
    """Extract cancer type from clinical text.

    Args:
        text: Clinical text to analyze.

    Returns:
        Canonical cancer type name or None.
    """
    if not text:
        return None
    ...
```

## Adding New Cancer Types

1. Edit `backend/config.py`:
   ```python
   CANCER_KEYWORDS = [
       ...
       (["kolon kanseri", "kolon karsinomu", "kolorektal"], "Kolon kanseri"),
   ]
   ```

2. Optionally add ICD-10 mapping:
   ```python
   ICD10_CANCER_MAPPING = {
       ...
       "C18": "Kolon kanseri",
   }
   ```

3. Add fallback protocol in `rag_engine.py`:
   ```python
   fallback_map = {
       ...
       "kolon kanseri": {
           "recommended_labs": ["CEA", "CA-19.9", "Hb"],
           "treatment_protocol": "...",
       },
   }
   ```

4. Regenerate data:
   ```bash
   python -m backend.export_data
   ```

## Debugging

### API Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m backend.api

# Test endpoint
curl -v http://localhost:8000/health
```

### RAG System Debugging
```python
# Check ChromaDB status
from backend.rag_engine import check_rag_system
print(check_rag_system())

# Query similar patients
from backend.rag_engine import query_similar_patients
print(query_similar_patients("meme kanseri"))

# Query by text
from backend.rag_engine import query_similar_patients_by_text
print(query_similar_patients_by_text("meme kanseri kemoterapi"))
```

### Data Processing Debugging
```python
from backend.data_processor import load_dataset, process_patient

df = load_dataset()
print(f"Columns: {df.columns.tolist()}")
print(f"Shape: {df.shape}")

# Process first row
patient = process_patient(df.iloc[0])
print(patient)
```

## Common Issues

### Knowledge base not found
```bash
python -m backend.export_data
```

### ChromaDB not ready
```bash
rm -rf data/chroma
python -m backend.export_data
```

### Ollama connection failed
- Check Ollama is running: `ollama list`
- Verify `OLLAMA_HOST` environment variable
- System works without Ollama (fallback mode)

### CORS errors
Set `ALLOWED_ORIGINS` to your domain:
```bash
export ALLOWED_ORIGINS="https://yourdomain.com"
```

### ModuleNotFoundError
```bash
export PYTHONPATH="$PWD"
# Or use direnv:
direnv allow
```

## Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# ICD-10 prediction
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "meme kanseri", "cancer_type": "Meme Kanseri"}'

# Treatment recommendation
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "meme kanseri"}'

# Patient summary
curl -X POST http://localhost:8000/analyze/summary \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "60 yaşında meme kanseri hastası"}'

# Risk assessment
curl -X POST http://localhost:8000/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "Metastatik meme kanseri", "lab_text": "AST: 120"}'
```

### Load Testing
```bash
ab -n 100 -c 10 http://localhost:8000/health
```
