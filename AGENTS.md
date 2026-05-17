# SPECTRA - Agent Guide

Clinical decision helper (Risk Report + Patient Summary + ICD-10 Coding) for Turkish healthcare.
Popup/overlay frontend served by FastAPI. Uses ChromaDB + Ollama for RAG-based analysis.

## Quick Start

```bash
# 1. Dependencies
pip install -r requirements.txt

# 2. Ollama (optional - fallback works without)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M

# 3. Generate data + index ChromaDB (required - data/ is .gitignored)
python -m backend.export_data

# 4. Run (single process — serves frontend + API)
python -m backend.api                    # Port 8000 — frontend at http://localhost:8000
# or with auto-reload:
uvicorn backend.api:app --reload --port 8000
```

## Architecture

```
Doctor's HBYS website (e.g. Pusula)
        └── SPECTRA popup overlay (index.html served by FastAPI at GET /)
                │
                └── FastAPI (8000)
                      ├── POST /predict/icd10      ← ICD-10 code matching
                      ├── POST /analyze/summary     ← RAG + LLM patient summary
                      ├── POST /analyze/risk        ← RAG + LLM risk assessment
                      └── POST /recommend/treatment ← fallback protocols
```

- Single process: `python -m backend.api` serves both frontend HTML and API endpoints
- No Streamlit, no separate frontend server
- CORS allows all origins by default (`ALLOWED_ORIGINS=*`)
- All analysis has RAG+LLM (Ollama) and fallback (rule-based) paths

## Module Structure

```
backend/
├── __init__.py             # Package metadata
├── config.py               # All constants, env vars, patterns (single source of truth)
├── exceptions.py           # Custom exception hierarchy
├── utils.py                # Pure helper functions (no side effects)
├── models.py               # Pydantic request/response schemas
├── data_processor.py       # CSV/Excel loading, cleaning, training pairs
├── rag_engine.py           # ChromaDB + Ollama RAG pipeline + fallbacks
├── api.py                  # FastAPI application and routes
├── export_data.py          # Data export pipeline orchestrator
└── cancer_classifier.py    # XGBoost model (optional, separate pipeline)
```

## PYTHONPATH Requirement

All `python -m backend.*` commands need project root on `PYTHONPATH`.
This is set automatically by `.envrc` (direnv) and `shell.nix` / `devenv.nix`.
If not using those:

```bash
export PYTHONPATH="$PWD"
```

## Environment Setup Options

| Method | Auto-activates venv | Sets PYTHONPATH |
|--------|---------------------|------------------|
| `direnv allow` (`.envrc`) | Yes | Yes |
| `nix-shell` (`shell.nix`) | Yes (creates if missing) | Yes |
| `devenv shell` (`devenv.nix`) | No | Yes |
| Manual `source venv/bin/activate` | Yes | **No** — must set manually |

## Key Commands

```bash
# API (with auto-reload)
uvicorn backend.api:app --reload --port 8000

# Export/regenerate data files
python -m backend.export_data

# Train XGBoost cancer classifier (separate feature)
python -m backend.cancer_classifier

# LoRA fine-tune Qwen2 on patient Q&A data
python train.py --use_lora --epochs 3

# Debug: check ChromaDB status
python -c "from backend.rag_engine import check_rag_system; print(check_rag_system())"

# Debug: query similar patients
python -c "from backend.rag_engine import query_similar_patients; print(query_similar_patients('meme kanseri'))"

# Health check
curl http://localhost:8000/health
```

## Gitignored Directories (agent must generate)

| Path | Contents | Created by |
|------|----------|------------|
| `data/` | knowledge_base.json, training_data.json, cleaned_patients.csv | `python -m backend.export_data` |
| `models/` | cancer_classifier.joblib, feature_scaler.joblib, label_encoder.joblib | `python -m backend.cancer_classifier` or `python train.py` |

Neither `data/` nor `models/` exist in the repo. **Always run `export_data.py` first.**

## ChromaDB Timing

`data/chroma/` is created by `export_data.py` at export time (via `index_patient_data()` in `rag_engine.py`). The `/health` endpoint checks it at startup.

Clear `data/chroma/` and re-run `export_data.py` to force a rebuild.

## Testing

There is **no test framework** in this repo. Verification is manual:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "test", "cancer_type": "meme kanseri"}'
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "meme kanseri"}'
curl -X POST http://localhost:8000/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "Metastatik meme kanseri", "lab_text": "AST: 120"}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Frontend popup UI |
| `/api` | GET | API information |
| `/health` | GET | System status (KB loaded, Chroma ready, Ollama available) |
| `/predict/icd10` | POST | ICD-10 codes from clinical notes |
| `/recommend/treatment` | POST | Treatment recommendations (RAG+LLM or fallback) |
| `/analyze/summary` | POST | Patient summary from clinical text (RAG+LLM or fallback) |
| `/analyze/risk` | POST | Risk assessment from clinical text + labs (RAG+LLM or fallback) |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc UI |

### Request size limits
- `clinical_note` / `clinical_text` max 10,000 characters (enforced by Pydantic)
- Ollama API timeout: 120 seconds
- Frontend API timeout: 30 seconds (treatment), 15 seconds (ICD-10)

## Supported Cancer Types (Turkish)

Defined in `backend/config.py:CANCER_KEYWORDS`. To add a new cancer type, edit `config.py` and re-run `export_data.py`.

| Cancer Type | ICD-10 Prefix |
|-------------|---------------|
| Karaciğer kanseri | C22 |
| Meme Kanseri | C50 |
| Multipl miyelom | C90 |
| Over kanseri | C56 |
| Prostat kanseri | C61 |
| Akciğer kanseri | C34 |
| Kolon kanseri | C18 |
| Pankreas kanseri | C25 |
| Mide kanseri | C16 |
| Mesane kanseri | C67 |
| Böbrek kanseri | C64 |
| Lenfoma | C81-C85 |
| Lösemi | C91-C95 |
| Tiroid kanseri | C73 |
| Baş boyun kanseri | C00-C14 |
| Endometriyum kanseri | C54 |
| Serviks kanseri | C53 |
| Malign melanom | C43 |

## Data Pipeline

```
hackathon_veri.csv (raw CSV, 365K rows, 31 columns — must exist at project root)
    ↓
backend/data_processor.py — load, clean, extract cancer types from text, lab values, drugs
    ↓
backend/export_data.py
    ├── data/knowledge_base.json    — ICD-10 code → cancer_type mappings
    ├── data/training_data.json     — Q&A pairs for LoRA fine-tuning
    ├── data/cleaned_patients.csv   — Structured patient data
    └── data/chroma/                — Vector database (indexed by index_patient_data())
```

The knowledge_base.json entry format:
```json
{
  "code": "C22.0",
  "cancer_types": ["Karaciğer kanseri"],
  "description": "Full ICD-10 string from source Excel"
}
```

## ML Training (Separate Pipelines)

### XGBoost Cancer Classifier (`backend/cancer_classifier.py`)
- Classifies cancer type from lab values (17 lab columns)
- Trained with: XGBoost, StandardScaler, LabelEncoder
- Outputs: `models/cancer_classifier.joblib`, `models/feature_scaler.joblib`, `models/label_encoder.joblib`
- Requires `xgboost` and `scikit-learn`

### LoRA Fine-tuning (`train.py`)
- Fine-tunes Qwen2-1.8B on patient Q&A pairs
- Requires `requirements_vast.txt` (torch, transformers, peft, bitsandbytes, etc.)
- Default: `Qwen/Qwen2-1.8B`, 4-bit quantization, LoRA rank 16
- Output: `models/lora_adapter/`
- Usage: `python train.py --use_lora --epochs 3`

## Configuration

Environment variables (all optional with defaults):

```bash
OLLAMA_HOST=http://localhost:11434    # Ollama server URL
OLLAMA_MODEL=qwen2:7b-instruct-q5_K_M# Ollama model name
ALLOWED_ORIGINS=*                     # CORS origins (change in production)
LOG_LEVEL=INFO                        # Logging level
```

Variables are loaded via `python-dotenv` in `rag_engine.py`. Copy `.env.example` to `.env` to override.

## Key Files

| Path | Purpose |
|------|---------|
| `backend/config.py` | All constants, env vars, patterns (single source of truth) |
| `backend/api.py` | FastAPI app, lifespan events, route handlers |
| `backend/rag_engine.py` | ChromaDB client, Ollama API calls, fallback protocols, prompt builder |
| `backend/data_processor.py` | CSV/Excel loading, cleaning, ICD-10 extraction, training pair creation |
| `backend/export_data.py` | CLI entrypoint to generate all data files |
| `backend/models.py` | Pydantic request/response schemas |
| `backend/utils.py` | Pure helper functions |
| `backend/exceptions.py` | Custom exception hierarchy |
| `backend/cancer_classifier.py` | XGBoost model training (separate feature) |
| `index.html` | Popup overlay frontend (served by FastAPI at GET /) |
| `train.py` | LoRA fine-tuning script for Qwen2 |
| `data/knowledge_base.json` | ICD-10 mappings (required at API startup) |
| `data/chroma/` | ChromaDB persistent vector index (created at runtime) |
| `hackathon_veri.csv` | Source data — must exist at repo root (365K rows, 31 cols) |

## Response Format: Turkish Only

All system interactions use Turkish:
- Fallback protocol text is Turkish (hardcoded in `rag_engine.py`)
- LLM system prompt instructs Turkish responses
- Cancer types and lab names are Turkish
- Frontend displays treatment protocols and lab names in Turkish
- UI chrome labels (buttons, headings) are in English

ICD-10 code descriptions are in English (from the source Excel).

## ICD-10 Scoring Algorithm

In `backend/api.py`, each knowledge base entry is scored:

| Condition | Score |
|-----------|-------|
| `cancer_type` matches entry's `cancer_types` | +0.5 |
| Keyword from clinical note appears in description | +0.3 |
| ICD-10 code prefix (e.g., "C22") appears in note | +0.5 |

Top 10 results returned sorted by descending score.

## Fallback Protocols

When Ollama is unavailable (`rag_engine.py`):
- 5 predefined cancer types with hardcoded Turkish protocols
- Each includes recommended labs + 2-3 sentence treatment description
- Unknown cancer types get a generic response suggesting multidisciplinary review
- Source field in response: `"fallback"` vs `"rag+llm"`

## Common Issues

### Knowledge base not loaded (503 on /predict/icd10)
```bash
python -m backend.export_data
```

### ChromaDB not ready
```bash
rm -rf data/chroma
python -m backend.export_data
```

### Ollama connection refused
- Check `ollama list` — is the server running?
- Check `OLLAMA_HOST` env var
- API works fine without it; fallback protocols are used

### `ModuleNotFoundError: No module named 'backend'`
Forgot to set `PYTHONPATH`:
```bash
export PYTHONPATH="$PWD"
```

### Source CSV not found
`hackathon_veri.csv` must exist at the project root (114MB, 365K rows). It is **gitignored** — you must obtain it separately.
