# SPECTRA - Oncology Assistant

## System for Predictive Evaluation, Clinical Triage & Risk Assessment

AI-powered oncology decision support for Turkish healthcare professionals.

---

## Features

### 1. ICD-10 Code Generator
- Generate ICD-10 diagnostic codes from clinical notes
- 20+ codes in knowledge base
- Supports: Karaciğer kanseri, Meme Kanseri, Multipl miyelom, Over kanseri, Prostat kanseri

### 2. Treatment Recommender
- Evidence-based treatment protocols
- Uses RAG + local LLM (Ollama/Qwen2)
- Fallback recommendations when LLM unavailable

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| RAG | ChromaDB |
| LLM | Ollama + Qwen2 |
| API | FastAPI |
| UI | Streamlit |

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Ollama + model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M

# Run API (Terminal 1)
python -m backend.api

# Run UI (Terminal 2)
streamlit run frontend/app.py
```

Open http://localhost:8501

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/predict/icd10` | POST | Generate ICD-10 codes |
| `/recommend/treatment` | POST | Get treatment recommendations |
| `/docs` | GET | Swagger documentation |

---

## Data Files

Required files (copy from source):
- `data/knowledge_base.json` - ICD-10 codes
- `data/chroma/` - Patient vector index

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | http://localhost:11434 | Ollama API URL |
| `ALLOWED_ORIGINS` | * | CORS origins |

---

## License

MIT