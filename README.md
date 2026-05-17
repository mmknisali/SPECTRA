# SPECTRA - Oncology Assistant

## System for Predictive Evaluation, Clinical Triage & Risk Assessment

AI-powered oncology decision support for Turkish healthcare professionals.

---

## Features

### 1. Clinical Decision Popup (3-Tab Interface)
Served directly from FastAPI at `GET /` — an overlay HTML popup designed to run inside a doctor's HBYS (Hospital Information System):

- **Risk Report** — Risk level assessment (düşük/orta/yüksek), risk factors, abnormal lab values, metastasis indicators, and clinical recommendations
- **Patient Summary** — Cancer type, stage, treatment history, current medications, key findings, and performance status
- **ICD-10 Codes** — Score-ranked ICD-10 code suggestions based on clinical note keywords and cancer type matching

### 2. ICD-10 Code Generator
- Generate ICD-10 diagnostic codes from clinical notes in Turkish
- 100+ codes in knowledge base covering major cancer types
- Score-based matching using cancer type + clinical note keywords

### 3. Patient Summary & Risk Assessment
- Structured patient summary extraction from free-text clinical notes
- Risk level classification with flagged abnormal lab values
- Metastasis indicator detection from clinical text
- RAG (Retrieval-Augmented Generation) using ChromaDB + Ollama LLM
- Rule-based fallback when LLM unavailable

### 4. Treatment Recommender
- Evidence-based treatment protocols from historical patient data
- RAG using ChromaDB + Ollama LLM
- Fallback to hardcoded protocols when LLM unavailable
- Optional lab value integration for personalized recommendations
- All responses in Turkish with localized drug names

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| RAG | ChromaDB (vector database) |
| LLM | Ollama + Qwen2:7b-instruct-q5_K_M |
| API + Frontend | FastAPI (serves HTML popup) |
| Data | Pandas, OpenPyXL |

---

## Quick Start

### Prerequisites
- Python 3.11+
- 8GB RAM (for LLM inference)
- ~5GB disk space

### Installation

```bash
# 1. Clone and install dependencies
pip install -r requirements.txt

# 2. Install Ollama (optional - fallback works without)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M

# 3. Export data from CSV (creates knowledge_base.json + ChromaDB index)
python -m backend.export_data

# 4. Start the API (single process — serves frontend + backend)
python -m backend.api          # http://localhost:8000
```

### First Time Setup
```bash
python -m backend.export_data
```

This creates:
- `data/knowledge_base.json` — ICD-10 code mappings (required for API)
- `data/training_data.json` — Q&A training pairs
- `data/chroma/` — ChromaDB vector index for RAG

---

## Project Structure

```
SPECTRA/
├── backend/
│   ├── api.py              # FastAPI entry point (serves index.html + API endpoints)
│   ├── rag_engine.py       # RAG + LLM integration (summary, risk, treatment)
│   ├── data_processor.py   # Data loading and cleaning (CSV pipeline)
│   ├── export_data.py      # Generate KB + index ChromaDB
│   └── cancer_classifier.py # ML cancer type classifier
├── index.html              # Frontend popup UI (served by FastAPI at GET /)
├── data/
│   ├── knowledge_base.json # ICD-10 codes (generated)
│   ├── training_data.json  # Q&A training pairs (generated)
│   └── chroma/             # ChromaDB vectors (generated)
├── docs/
│   ├── api.md              # API documentation
│   ├── development.md      # Development guide
│   └── deployment.md       # Deployment options
├── models/                 # Trained ML models
│   ├── cancer_classifier.joblib
│   └── lora_adapter/       # Fine-tuned LLM adapter
├── hackathon_veri.csv      # Source data (365K rows, 31 columns)
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the SPECTRA popup frontend (`index.html`) |
| `/api` | GET | API information |
| `/health` | GET | System health (KB, Chroma, Ollama) |
| `/predict/icd10` | POST | Generate ICD-10 codes from clinical notes |
| `/recommend/treatment` | POST | Get treatment recommendations |
| `/analyze/summary` | POST | Extract structured patient summary |
| `/analyze/risk` | POST | Generate risk assessment |
| `/docs` | GET | Swagger/OpenAPI documentation |

See [docs/api.md](docs/api.md) for full API reference.

---

## Configuration

Environment variables (all optional with sensible defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | http://localhost:11434 | Ollama API URL |
| `OLLAMA_MODEL` | qwen2:7b-instruct-q5_K_M | Model name |
| `ALLOWED_ORIGINS` | * | CORS origins |

Create `.env` file for local overrides (see `.env.example`).

---

## Usage

### ICD-10 Code Generation
```bash
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_note": "Patient presents with liver mass, elevated AST/ALT",
    "cancer_type": "Karaciğer kanseri"
  }'
```

### Treatment Recommendation
```bash
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{
    "cancer_type": "Karaciğer kanseri",
    "patient_labs": {
      "ast": 120,
      "alt": 95
    }
  }'
```

### Patient Summary Extraction
```bash
curl -X POST http://localhost:8000/analyze/summary \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_text": "65 yasinda meme kanseri hastasi, opere, 4 kür kemoterapi almis",
    "lab_text": "AST: 35, ALT: 28, CRP: 3"
  }'
```

### Risk Assessment
```bash
curl -X POST http://localhost:8000/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_text": "Ileri evre over kanseri, karaciger metastazi mevcut",
    "lab_text": "CA-125: 350, AST: 85, ALT: 92"
  }'
```

---

## Running Without Ollama

The API starts without Ollama and uses fallback protocols:
- ICD-10 generation works from knowledge base
- Patient summary and risk assessment use rule-based fallback
- Treatment recommendations use hardcoded Turkish protocols
- System logs warnings but remains functional

To run without LLM, simply skip the Ollama setup step.

---

## Documentation

- [API Reference](docs/api.md) — Complete endpoint documentation
- [Development Guide](docs/development.md) — Setup, debugging, and contributing
- [Deployment Guide](docs/deployment.md) — Production deployment options

---

## Data Pipeline

1. **Source**: `hackathon_veri.csv` (365K rows, 31 columns — patient records from Turkish healthcare)
2. **Processing**: `backend/export_data.py` exports:
   - ICD-10 knowledge base (`knowledge_base.json`)
   - Training pairs for fine-tuning (`training_data.json`)
3. **Vector Store**: ChromaDB indexed during export (`python -m backend.export_data`), not at runtime
4. **Knowledge Base**: JSON file loaded at API startup

---

## System Architecture

```
Doctor's HBYS Website
        │
        ▼ (iframe / popup overlay)
┌────────────────────────────────┐
│    SPECTRA Popup (index.html)  │
│  ┌─────────┬────────┬────────┐ │
│  │ Risk    │Patient │ ICD-10 │ │
│  │ Report  │Summary │ Codes  │ │
│  └─────────┴────────┴────────┘ │
└──────────────┬─────────────────┘
               │ POST /analyze/risk, /analyze/summary, /predict/icd10
               ▼
        FastAPI (port 8000)
         ┌──────┴──────┐
         │              │
    ChromaDB         Ollama (optional)
   (vectors)        Fallback (always)
```

- Frontend auto-detects API URL via `window.location.origin` (no `API_BASE_URL` needed)
- API loads knowledge base and checks ChromaDB at startup
- RAG queries ChromaDB for similar patients to enrich LLM context
- If Ollama available → LLM generates structured responses
- If Ollama unavailable → rule-based fallback used for all features

---

## Contributing

See [docs/development.md](docs/development.md) for:
- Development setup
- Code structure
- Adding new cancer types
- Testing

---

## License

MIT License — See LICENSE file
