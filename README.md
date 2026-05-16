# SPECTRA - Oncology Assistant

## System for Predictive Evaluation, Clinical Triage & Risk Assessment

AI-powered oncology decision support for Turkish healthcare professionals.

---

## Features

### 1. ICD-10 Code Generator
- Generate ICD-10 diagnostic codes from clinical notes in Turkish
- 20+ codes in knowledge base covering major cancer types
- Supports: Karaciğer kanseri, Meme Kanseri, Multipl miyelom, Over kanseri, Prostat kanseri
- Score-based matching using cancer type + clinical note keywords

### 2. Treatment Recommender
- Evidence-based treatment protocols from historical patient data
- RAG (Retrieval-Augmented Generation) using ChromaDB + Ollama LLM
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
| API | FastAPI (uvicorn) |
| UI | Streamlit |
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

# 3. Export data from source Excel (creates knowledge_base.json)
python -m backend.export_data

# 4. Start services (run in separate terminals)
python -m backend.api          # API on http://localhost:8000
streamlit run frontend/app.py  # UI on http://localhost:8501
```

### First Time Setup
The first time you run, you'll need to export the data:
```bash
python -m backend.export_data
```

This creates three files in `data/`:
- `knowledge_base.json` - ICD-10 code mappings (required for API)
- `training_data.json` - Q&A training pairs
- `cleaned_patients.csv` - Processed patient records

---

## Project Structure

```
SPECTRA/
├── backend/
│   ├── api.py              # FastAPI entry point
│   ├── rag_engine.py       # RAG + LLM integration
│   ├── data_processor.py   # Data loading and cleaning
│   ├── export_data.py      # Generate KB from Excel
│   └── cancer_classifier.py # ML cancer type classifier
├── frontend/
│   └── app.py              # Streamlit UI
├── data/
│   ├── knowledge_base.json # ICD-10 codes (generated)
│   └── chroma/             # ChromaDB vectors (generated)
├── docs/
│   ├── api.md              # API documentation
│   ├── development.md      # Development guide
│   └── deployment.md       # Deployment options
├── models/                 # Trained ML models
│   ├── cancer_classifier.joblib
│   └── lora_adapter/       # Fine-tuned LLM adapter
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | System health (KB, Chroma, Ollama) |
| `/predict/icd10` | POST | Generate ICD-10 codes |
| `/recommend/treatment` | POST | Get treatment recommendations |
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
| `API_BASE_URL` | http://localhost:8000 | Frontend → API URL |

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

---

## Running Without Ollama

The API starts without Ollama and uses fallback protocols:
- ICD-10 generation works from knowledge base
- Treatment recommendations use hardcoded Turkish protocols
- System logs warnings but remains functional

To run without LLM, simply skip the Ollama setup step.

---

## Documentation

- [API Reference](docs/api.md) - Complete endpoint documentation
- [Development Guide](docs/development.md) - Setup, debugging, and contributing
- [Deployment Guide](docs/deployment.md) - Production deployment options

---

## Data Pipeline

1. **Source**: `datamedx_veriset_26.xlsx` (raw patient data)
2. **Processing**: `backend/export_data.py` exports:
   - ICD-10 knowledge base
   - Training pairs for fine-tuning
   - Cleaned patient records
3. **Vector Store**: ChromaDB indexes patient records for RAG
4. **Knowledge Base**: JSON file loaded at API startup

---

## System Architecture

```
User → Streamlit UI (8501) → FastAPI (8000) → ChromaDB (vectors)
                                      ↓
                              Ollama (optional)
                              Fallback (always)
```

- Frontend polls `/health` endpoint for connection status
- API loads knowledge base at startup
- RAG queries ChromaDB for similar patients
- If Ollama available → LLM generates response
- If Ollama unavailable → fallback protocols used

---

## Contributing

See [docs/development.md](docs/development.md) for:
- Development setup
- Code structure
- Adding new cancer types
- Testing

---

## License

MIT License - See LICENSE file
