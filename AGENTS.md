# SPECTRA - Agent Guide

Oncology assistant (ICD-10 coding + treatment recommendations) for Turkish healthcare. Python 3.11+ project using FastAPI + Streamlit + ChromaDB + Ollama.

## Quick Start

```bash
# 1. Dependencies
pip install -r requirements.txt

# 2. Ollama (optional - fallback works without)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M

# 3. Generate data (required - data/ is .gitignored)
python -m backend.export_data

# 4. Run API (terminal 1)
python -m backend.api                    # Port 8000
# or with auto-reload during development:
uvicorn backend.api:app --reload --port 8000

# 5. Run frontend (terminal 2)
streamlit run frontend/app.py            # Port 8501
```

## Architecture

```
Streamlit (8501) ──→ FastAPI (8000) ──→ ChromaDB (vector index)
                              │
                      Ollama (optional)
                      Fallback (always available)
```

- API starts without Ollama; treatment falls back to hardcoded Turkish protocols
- ICD-10 prediction is entirely knowledge-base-driven (no LLM needed)
- Frontend polls `/health` to show connection status in sidebar
- CORS allows all origins by default (`ALLOWED_ORIGINS=*`)

## PYTHONPATH Requirement

All `python -m backend.*` commands need project root on `PYTHONPATH`.
This is set automatically by `.envrc` (direnv) and `shell.nix` / `devenv.nix`.
If not using those, export manually:

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

The `.envrc` also fixes `LD_LIBRARY_PATH` for Nix's gcc libstdc++.

## Key Commands

```bash
# API (with auto-reload)
uvicorn backend.api:app --reload --port 8000

# Export/regenerate data files
python -m backend.export_data

# Train XGBoost cancer classifier (separate feature, not in main flow)
python -m backend.cancer_classifier

# LoRA fine-tune Qwen2 on patient Q&A data (requires requirements_vast.txt)
python train.py --use_lora --epochs 3

# Debug: check ChromaDB status
python -c "from backend.rag_engine import check_rag_system; print(check_rag_system())"

# Debug: query similar patients from ChromaDB
python -c "from backend.rag_engine import query_similar_patients; print(query_similar_patients('meme kanseri'))"

# Health check
curl http://localhost:8000/health
```

## Gitignored Directories (agent must generate)

| Path | Contents | Created by |
|------|----------|------------|
| `data/` | knowledge_base.json, training_data.json | `python -m backend.export_data` |
| `models/` | cancer_classifier.joblib, feature_scaler.joblib, label_encoder.joblib, lora_adapter/ | `python -m backend.cancer_classifier` or `python train.py` |

Neither `data/` nor `models/` exist in the repo. **Always run `export_data.py` first.**
Note: `data/cleaned_patients.csv` would be created if `export_cleaned_data()` were called in `export_data.py:main()`, but it is not — only `knowledge_base.json` and `training_data.json` are actually exported.

## ChromaDB Timing

`data/chroma/` is **not** created by `export_data.py`. ChromaDB rebuilds its persistent index at API runtime when the first query hits `check_rag_system()` or `get_treatment_recommendation()`. The `/health` endpoint triggers this at startup.

Clear `data/chroma/` to force a rebuild.

## Testing

There is **no test framework** in this repo. No pytest config, no test directory, no CI workflows. Verification is manual:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "test", "cancer_type": "meme kanseri"}'
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "meme kanseri"}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | System status (KB loaded, Chroma ready, Ollama available) |
| `/predict/icd10` | POST | ICD-10 codes from clinical notes |
| `/recommend/treatment` | POST | Treatment recommendations (RAG+LLM or fallback) |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc UI |

### Request size limits
- `clinical_note` max 10,000 characters (enforced by Pydantic)
- Ollama API timeout: 120 seconds
- Frontend API timeout: 30 seconds (treatment), 15 seconds (ICD-10)

## Supported Cancer Types (Turkish)

Hardcoded in three locations that must stay in sync:

| Cancer Type | ICD-10 Prefix | Location |
|-------------|---------------|----------|
| Karaciğer kanseri | C22 | `data_processor.py:74`, `rag_engine.py:170`, `frontend/app.py:145` |
| Meme Kanseri | C50 | `data_processor.py:77-78`, `rag_engine.py:174`, `frontend/app.py:146` |
| Multipl miyelom | C90 | `data_processor.py:82`, `rag_engine.py:178`, `frontend/app.py:147` |
| Over kanseri | C56 | `data_processor.py:79-80`, `rag_engine.py:182`, `frontend/app.py:148` |
| Prostat kanseri | C61 | `data_processor.py:81`, `rag_engine.py:186`, `frontend/app.py:149` |

To add a new cancer type, edit **all three** files and regenerate.

## Data Pipeline

```
datamedx_veriset_26.xlsx (raw Excel, must exist at project root)
    ↓
backend/data_processor.py — load, clean, extract ICD-10 codes, lab values, drugs
    ↓
backend/export_data.py
    ├── data/knowledge_base.json    — ICD-10 code → cancer_type mappings
    └── data/training_data.json     — Q&A pairs for LoRA fine-tuning
Note: `export_cleaned_data()` exists but is NOT called from `main()`.
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

These are side features, not required for the main app to run.

### XGBoost Cancer Classifier (`backend/cancer_classifier.py`)
- Classifies cancer type from lab values (17 lab columns)
- Trained with: XGBoost, StandardScaler, LabelEncoder
- Outputs models: `cancer_classifier.joblib`, `feature_scaler.joblib`, `label_encoder.joblib`
- Requires `xgboost` and `scikit-learn` (NOT in `requirements.txt`; install manually or via `shell.nix`)

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
API_BASE_URL=http://localhost:8000    # Frontend → API URL (used by Streamlit)
```

Variables are loaded via `python-dotenv` in `rag_engine.py`. Copy `.env.example` to `.env` to override.

## Key Files

| Path | Purpose |
|------|---------|
| `backend/api.py` | FastAPI app, lifespan events, route handlers, Pydantic models |
| `backend/rag_engine.py` | ChromaDB client, Ollama API calls, fallback protocols, prompt builder |
| `backend/data_processor.py` | Excel loading, cleaning, ICD-10 extraction, training pair creation |
| `backend/export_data.py` | CLI entrypoint to generate all data files from Excel |
| `backend/cancer_classifier.py` | XGBoost model training (separate feature) |
| `frontend/app.py` | Streamlit UI, dark theme, two-tab layout |
| `train.py` | LoRA fine-tuning script for Qwen2 (separate entrypoint) |
| `data/knowledge_base.json` | ICD-10 mappings (required at API startup) |
| `data/chroma/` | ChromaDB persistent vector index (created at runtime) |
| `datamedx_veriset_26.xlsx` | Source data — must exist at repo root for export |
| `docs/api.md` | Full API documentation |
| `docs/development.md` | Development guide with debugging tips |
| `docs/deployment.md` | Docker, cloud, and production deployment |

## Response Format: Turkish Only

All system interactions use Turkish:
- Fallback protocol text is Turkish (hardcoded in `rag_engine.py:167-203`)
- LLM system prompt instructs Turkish responses (`rag_engine.py:23-38`)
- Cancer types and lab names are Turkish (`frontend/app.py`)
- Frontend displays treatment protocols and lab names in Turkish
- UI chrome labels (buttons, headings) are in English

ICD-10 code descriptions are in English (from the source Excel).

## ICD-10 Scoring Algorithm

In `backend/api.py:171-194`, each knowledge base entry is scored:

| Condition | Score |
|-----------|-------|
| `cancer_type` matches entry's `cancer_types` | +0.5 |
| Keyword from clinical note appears in description | +0.3 |
| ICD-10 code prefix (e.g., "C22") appears in note | +0.5 |

Top 10 results returned sorted by descending score.

## Fallback Protocols

When Ollama is unavailable (`rag_engine.py:167-203`):
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
mkdir -p data/chroma   # directory must exist and be writable
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

### Source Excel not found
`datamedx_veriset_26.xlsx` must exist at the project root. It is **not** gitignored and should be present in the repo.
