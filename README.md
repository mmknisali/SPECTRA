# SPECTRA — Clinical Decision Support System

> **S**tructured **P**atient **E**valuation & **C**linical **T**reatment **R**isk **A**ssistant

SPECTRA is a clinical decision support tool designed for Turkish healthcare providers. It overlays as a popup on existing hospital information systems (HBYS) and provides three analysis capabilities:

| Tab | Purpose | Method |
|-----|---------|--------|
| **Risk Report** | Risk assessment from clinical text + labs | RAG + LLM (Ollama) → fallback |
| **Patient Summary** | Structured summary extraction | RAG + LLM (Ollama) → fallback |
| **ICD-10 Codes** | Diagnostic code suggestions | Knowledge base scoring |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Doctor's HBYS (e.g. Pusula)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  SPECTRA Popup (index.html)                       │  │
│  │  ┌─────────┐ ┌──────────────┐ ┌────────────────┐ │  │
│  │  │  Risk   │ │   Patient    │ │   ICD-10       │ │  │
│  │  │ Report  │ │   Summary    │ │   Codes        │ │  │
│  │  └─────────┘ └──────────────┘ └────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (fetch)
                         ▼
              ┌──────────────────────┐
              │  FastAPI (port 8000) │
              │                      │
              │  POST /analyze/risk  │
              │  POST /analyze/summary│
              │  POST /predict/icd10 │
              │  POST /recommend/    │
              │    treatment         │
              └──────┬───────┬───────┘
                     │       │
              ┌──────▼──┐ ┌──▼────────┐
              │ChromaDB │ │  Ollama   │
              │(RAG)    │ │  (LLM)    │
              └─────────┘ └───────────┘
                           │ (unavailable?)
                           ▼
                     ┌──────────┐
                     │ Fallback │
                     │ (rules)  │
                     └──────────┘
```

### Module Structure

```
backend/
├── __init__.py             # Package metadata
├── config.py               # All constants, env vars, patterns
├── exceptions.py           # Custom exception hierarchy
├── utils.py                # Pure helper functions
├── models.py               # Pydantic request/response schemas
├── data_processor.py       # CSV/Excel loading, cleaning, training pairs
├── rag_engine.py           # ChromaDB + Ollama RAG pipeline + fallbacks
├── api.py                  # FastAPI application and routes
├── export_data.py          # Data export pipeline orchestrator
└── cancer_classifier.py    # XGBoost model (optional, separate pipeline)
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Data

```bash
python -m backend.export_data
```

This creates:
- `data/knowledge_base.json` — ICD-10 code mappings
- `data/training_data.json` — Q&A pairs for LoRA fine-tuning
- `data/cleaned_patients.csv` — Structured patient data
- `data/chroma/` — ChromaDB vector index

### 3. Start the API

```bash
python -m backend.api
```

Open **http://localhost:8000** in your browser.

---

## Data Pipeline

```
hackathon_veri.csv (365K rows, 31 columns)
    │
    ▼
data_processor.py
    ├── load_dataset()        — Read CSV or Excel
    ├── process_patient()     — Extract structured fields
    ├── extract_cancer_type() — Keyword matching (18 types)
    ├── extract_lab_values()  — Structured columns + text parsing
    └── extract_drugs()       — Bracket-delimited drug names
    │
    ▼
export_data.py
    ├── create_training_pairs()     — 4 templates × N patients
    ├── create_icd10_knowledge_base() — ICD-10 → cancer_type map
    └── index_patient_data()        — ChromaDB bulk indexing
    │
    ▼
data/
    ├── knowledge_base.json
    ├── training_data.json
    ├── cleaned_patients.csv
    └── chroma/
```

### CSV Columns Used

| Column | Purpose |
|--------|---------|
| `epikriz` | Clinical notes (primary source for cancer type) |
| `hikaye` | Patient history (secondary source) |
| `lab_sonuclari` | Lab results (text format) |
| `ilac` | Medications (bracket-delimited) |
| `icd10` | ICD-10 codes (for knowledge base) |
| `kanser_turu` | Cancer type (if available) |
| `cinsiyet` | Gender |
| `department` | Department |
| 17 lab columns | Numeric lab values (hba1c, üre, kreatinin, etc.) |

---

## Analysis Flow

### Risk Assessment (`POST /analyze/risk`)

```
clinical_text + lab_text
    │
    ├── LLM path (Ollama available):
    │   1. Extract labs from text
    │   2. Flag abnormal values
    │   3. Query ChromaDB for similar patients
    │   4. Build prompt with context
    │   5. Call Ollama with RISK_SYSTEM_PROMPT
    │   6. Parse JSON response
    │
    └── Fallback path (Ollama unavailable):
        1. Keyword scan for risk factors
        2. Lab range checking
        3. Metastasis site detection
        4. Score-based risk level (≥4=yüksek, ≥2=orta, <2=düşük)
    │
    ▼
{
  "risk_level": "yüksek",
  "risk_factors": ["Metastaz varlığı", ...],
  "abnormal_labs": ["AST: 120 (YÜKSEK, normal: 0-40)", ...],
  "metastasis_indicators": ["karaciğer metastazı", ...],
  "recommendations": [...],
  "source": "rag+llm"  // or "fallback"
}
```

### Patient Summary (`POST /analyze/summary`)

```
clinical_text + lab_text
    │
    ├── LLM path:
    │   1. Extract cancer type from text
    │   2. Query ChromaDB for similar patients
    │   3. Build prompt with context
    │   4. Call Ollama with SUMMARY_SYSTEM_PROMPT
    │   5. Parse JSON response
    │
    └── Fallback path:
        1. Keyword cancer extraction
        2. Drug name extraction from brackets
        3. Treatment keyword scan (opere, kemoterapi, radyoterapi)
    │
    ▼
{
  "cancer_type": "Meme Kanseri",
  "stage": "Evre IIB",
  "treatment_history": ["Cerrahi geçirmiş", "Kemoterapi almış"],
  "current_medications": ["Tamoksifen"],
  "key_findings": [...],
  "performance_status": "ECOG 1",
  "source": "rag+llm"
}
```

### ICD-10 Coding (`POST /predict/icd10`)

```
clinical_note + cancer_type (optional)
    │
    └── Knowledge base scoring:
        For each KB entry:
            +0.5 if cancer_type matches entry's cancer_types
            +0.3 if any search term appears in description
            +0.5 if code prefix (e.g. "C22") appears in note
        Sort by score descending, return top 10
    │
    ▼
{
  "suggested_codes": [
    {"code": "C50.9", "description": "...", "score": 1.3, "cancer_types": ["Meme Kanseri"]},
    ...
  ],
  "source": "knowledge_base"
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2:7b-instruct-q5_K_M` | Ollama model name |
| `ALLOWED_ORIGINS` | `*` | CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Constants (in `backend/config.py`)

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_CLINICAL_NOTE_LENGTH` | 10000 | Max characters for clinical text |
| `OLLAMA_TIMEOUT` | 120 | Ollama API timeout (seconds) |
| `COLLECTION_NAME` | `spectra_knowledge` | ChromaDB collection name |
| `CANCER_KEYWORDS` | 18 entries | Cancer type keyword lists |
| `LAB_REFERENCE_RANGES` | 16 entries | Lab normal ranges |
| `ML_LAB_COLUMNS` | 17 columns | Lab columns for ML classifier |

---

## Supported Cancer Types

| Turkish Name | ICD-10 Prefix | Keywords (examples) |
|-------------|---------------|---------------------|
| Meme Kanseri | C50 | meme kanseri, meme karsinomu, meme ca |
| Karaciğer kanseri | C22 | karaciğer kanseri, hepatosellüler, hcc |
| Multipl miyelom | C90 | multipl miyelom, multiple myelom |
| Over kanseri | C56 | over kanseri, over karsinomu, yumurtalık |
| Prostat kanseri | C61 | prostat kanseri, prostat karsinomu |
| Akciğer kanseri | C34 | akciğer kanseri, lung cancer |
| Kolon kanseri | C18 | kolon kanseri, kolorektal |
| Pankreas kanseri | C25 | pankreas kanseri |
| Mide kanseri | C16 | mide kanseri, gastric |
| Mesane kanseri | C67 | mesane kanseri, bladder |
| Böbrek kanseri | C64 | böbrek kanseri, renal hücre |
| Lenfoma | C81-C85 | lenfoma, hodgkin |
| Lösemi | C91-C95 | lösemi |
| Tiroid kanseri | C73 | tiroid kanseri |
| Baş boyun kanseri | C00-C14 | baş boyun kanseri |
| Endometriyum kanseri | C54 | endometriyum, rahim kanseri |
| Serviks kanseri | C53 | serviks, rahim ağzı |
| Malign melanom | C43 | malign melanom, melanoma |

To add a new cancer type, edit **`backend/config.py`** (add to `CANCER_KEYWORDS` and optionally `ICD10_CANCER_MAPPING`), then re-run `export_data.py`.

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend popup UI |
| GET | `/api` | API information |
| GET | `/health` | System health status |
| POST | `/predict/icd10` | ICD-10 code prediction |
| POST | `/recommend/treatment` | Treatment recommendation |
| POST | `/analyze/summary` | Patient summary extraction |
| POST | `/analyze/risk` | Risk assessment |

### Health Check Response

```json
{
  "status": "healthy",
  "knowledge_base_loaded": true,
  "knowledge_base_size": 20,
  "chroma_ready": true,
  "chroma_documents": 499,
  "ollama_available": true,
  "ollama_models": 1
}
```

### Error Responses

| Status | Description |
|--------|-------------|
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 503 | Knowledge base not loaded |

Full API docs: http://localhost:8000/docs (Swagger UI)

---

## Deployment

### Local

```bash
pip install -r requirements.txt
python -m backend.export_data
python -m backend.api
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m backend.export_data
EXPOSE 8000
CMD ["python", "-m", "backend.api"]
```

### Production Checklist

- [ ] Run `export_data.py` to generate KB + ChromaDB
- [ ] Verify `data/chroma/` exists
- [ ] Test `/health` endpoint
- [ ] Set `ALLOWED_ORIGINS` to specific domains
- [ ] Enable HTTPS
- [ ] Configure log rotation

---

## Development

### Environment Setup

```bash
# Using direnv (recommended)
direnv allow

# Using nix-shell
nix-shell

# Using devenv
devenv shell
```

### Adding New Features

1. **New API endpoint**: Add Pydantic models in `models.py`, route in `api.py`, logic in `rag_engine.py`
2. **New data processing**: Add logic in `data_processor.py`, export in `export_data.py`
3. **New cancer type**: Add to `CANCER_KEYWORDS` in `config.py`, re-run `export_data.py`

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Risk assessment
curl -X POST http://localhost:8000/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "Metastatik meme kanseri, karaciğer metastazı", "lab_text": "AST: 120, ALT: 95"}'

# Patient summary
curl -X POST http://localhost:8000/analyze/summary \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "60 yaşında meme kanseri hastası, opere, kemoterapi alıyor"}'

# ICD-10 prediction
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "meme kanseri, meme ca tanısı", "cancer_type": "Meme Kanseri"}'
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Knowledge base not loaded | Run `python -m backend.export_data` |
| ChromaDB not ready | Delete `data/chroma/` and re-run `export_data` |
| Ollama connection refused | Check `ollama list`, verify `OLLAMA_HOST` env var |
| ModuleNotFoundError | Set `PYTHONPATH="$PWD"` or use `direnv allow` |
| Dataset not found | Place `hackathon_veri.csv` or `datamedx_veriset_26.xlsx` at project root |

---

## License

Internal use only.
