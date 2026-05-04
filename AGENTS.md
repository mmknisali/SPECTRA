# SPECTRA - Oncology Assistant

## System for Predictive Evaluation, Clinical Triage & Risk Assessment

AI-powered oncology decision support for Turkish healthcare professionals.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M

# Run API (Terminal 1)
python -m backend.api

# Run UI (Terminal 2)
streamlit run frontend/app.py
```

---

## Features

### ICD-10 Code Generator
- Generate ICD-10 codes from clinical notes
- 20+ codes in knowledge base

### Treatment Recommender
- Evidence-based treatment protocols
- Uses RAG + Ollama/Qwen2
- Fallback when LLM unavailable

---

## Architecture

```
┌──────────────────┐     ┌──────────────────┐
│  Streamlit UI     │────►│  FastAPI API     │
│  (Port 8501)     │     │  (Port 8000)     │
└──────────────────┘     └────────┬─────────┘
                                 │
              ┌────────────────────┼────────────────────┐
              ▼                                         ▼
    ┌──────────────────┐                    ┌──────────────────┐
    │  Ollama + Qwen2  │                    │  ChromaDB        │
    │  (LLM)          │                    │  Knowledge Base  │
    └──────────────────┘                    └──────────────────┘
```

---

## Requirements

| Resource | Minimum |
|----------|---------|
| RAM | 8GB |
| Storage | 5GB |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/predict/icd10` | POST | Generate ICD-10 codes |
| `/recommend/treatment` | POST | Treatment recommendations |
| `/docs` | GET | Swagger docs |

---

## Data Files

Required:
- `data/knowledge_base.json` - ICD-10 codes
- `data/chroma/` - Patient vector index

---

## Configuration

Environment variables:
- `OLLAMA_HOST` - Ollama URL (default: http://localhost:11434)
- `ALLOWED_ORIGINS` - CORS (default: *)