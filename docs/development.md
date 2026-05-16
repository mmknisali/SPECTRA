# Development Guide

Complete guide for developing and extending SPECTRA.

---

## Development Setup

### 1. Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Install dev tools
pip install pytest black flake8 mypy
```

### 2. Data Export (Required)
```bash
# Generate knowledge base and training data
python -m backend.export_data
```

This creates:
- `data/knowledge_base.json` - ICD-10 mappings
- `data/training_data.json` - Training pairs
- `data/cleaned_patients.csv` - Processed data

### 3. Start Development Servers

Terminal 1 - API:
```bash
# With auto-reload
python -m backend.api
# Or with uvicorn directly
uvicorn backend.api:app --reload --port 8000
```

Terminal 2 - Frontend:
```bash
streamlit run frontend/app.py
```

Access:
- Frontend: http://localhost:8501
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Project Structure Details

### Backend (`backend/`)

| File | Purpose |
|------|---------|
| `api.py` | FastAPI routes, request/response models, health checks |
| `rag_engine.py` | ChromaDB queries, Ollama integration, fallback protocols |
| `data_processor.py` | Excel loading, cleaning, ICD-10 extraction |
| `export_data.py` | Export processed data to JSON/CSV |
| `cancer_classifier.py` | ML model for cancer type prediction |

### Frontend (`frontend/`)

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI, API client, styling |

### Data Flow

```
Excel (.xlsx)
    ↓
data_processor.py (cleaning)
    ↓
export_data.py
    ├──→ knowledge_base.json
    ├──→ training_data.json
    └──→ cleaned_patients.csv
    ↓
ChromaDB (vector index created at runtime)
```

---

## Code Conventions

### Python Style
- Follow PEP 8
- Use type hints for function signatures
- Docstrings for all public functions
- Maximum line length: 100 characters

### Example:
```python
def get_treatment_recommendation(
    cancer_type: str,
    patient_labs: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Get treatment recommendation using RAG + LLM.
    
    Args:
        cancer_type: Turkish cancer type name
        patient_labs: Optional lab values for personalization
        
    Returns:
        Dict with recommended_labs, treatment_protocol, source
    """
    # Implementation
```

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`

---

## Adding New Cancer Types

### 1. Update ICD-10 Mappings
Edit `backend/data_processor.py`:
```python
def get_primary_cancer_type(icd10_codes: List[str]) -> Optional[str]:
    mapping = {
        'C22': 'Karaciğer kanseri',
        'C50': 'Meme Kanseri',
        # Add new mapping:
        'C18': 'Kolon kanseri',  # New!
    }
```

### 2. Add Fallback Protocol
Edit `backend/rag_engine.py`:
```python
def get_fallback_recommendation(cancer_type: str) -> Dict[str, Any]:
    fallback_map = {
        # Add new protocol
        "kolon kanseri": {
            "recommended_labs": ["CEA", "CA-19.9", "Hb", "Kreatinin"],
            "treatment_protocol": "Kolon kanserinde FOLFOX veya FOLFIRI..."
        }
    }
```

### 3. Update Frontend List
Edit `frontend/app.py`:
```python
CANCER_TYPES = [
    "Karaciğer kanseri",
    "Meme Kanseri",
    "Kolon kanseri",  # Add here
    # ...
]
```

### 4. Regenerate Data
```bash
python -m backend.export_data
```

---

## Debugging

### API Debugging
```bash
# Enable debug logging
export LOG_LEVEL=debug
python -m backend.api

# Test endpoint directly
curl -v http://localhost:8000/health
```

### RAG System Debugging
```bash
# Check ChromaDB status
python -c "from backend.rag_engine import check_rag_system; print(check_rag_system())"

# Query similar patients
python -c "from backend.rag_engine import query_similar_patients; print(query_similar_patients('meme kanseri'))"
```

### Frontend Debugging
```bash
# Run with detailed errors
streamlit run frontend/app.py --logger.level=debug
```

---

## Common Issues

### Issue: Knowledge base not found
**Error**: `Knowledge base not found - run export_data.py first`

**Fix**:
```bash
python -m backend.export_data
```

### Issue: ChromaDB not ready
**Error**: `ChromaDB client not available`

**Fix**: Check `data/chroma/` directory exists and is writable:
```bash
mkdir -p data/chroma
```

### Issue: Ollama connection failed
**Error**: Ollama unavailable in health check

**Fix**: 
- Check Ollama is running: `ollama list`
- Verify OLLAMA_HOST environment variable
- Or ignore - system uses fallback protocols

### Issue: CORS errors in browser
**Fix**: Set `ALLOWED_ORIGINS=*` or specify your domain

---

## Testing

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# ICD-10 prediction
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "test", "cancer_type": "meme kanseri"}'

# Treatment recommendation
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "meme kanseri"}'
```

### Load Testing
```bash
# Using ab (Apache Bench)
ab -n 100 -c 10 http://localhost:8000/health
```

---

## Environment Variables

Create `.env` file for local development:
```bash
# Ollama configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2:7b-instruct-q5_K_M

# CORS (for local dev)
ALLOWED_ORIGINS=*

# Frontend API URL
API_BASE_URL=http://localhost:8000
```

Load with:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Performance Optimization

### ChromaDB
- Index is created on first query (slow)
- Subsequent queries are fast
- Clear `data/chroma/` to rebuild

### API
- Knowledge base loaded once at startup
- Use `uvicorn --workers 4` for multi-process

### Frontend
- API calls cached in session state
- Health check polled every 5 seconds

---

## Adding New Features

### New API Endpoint
1. Add Pydantic models in `api.py`
2. Implement route handler
3. Add to `lifespan` if initialization needed
4. Update `docs/api.md`

### New Data Processing
1. Add cleaning logic in `data_processor.py`
2. Export in `export_data.py`
3. Regenerate data files
4. Test with `python -m backend.export_data`

### New UI Component
1. Add to `frontend/app.py`
2. Create API client function
3. Add error handling
4. Test both tabs work

---

## Deployment Checklist

Before deploying:
- [ ] Run `export_data.py` to generate KB
- [ ] Verify `data/chroma/` exists
- [ ] Test `/health` endpoint
- [ ] Test ICD-10 prediction
- [ ] Test treatment recommendation
- [ ] Verify Ollama or accept fallback
- [ ] Set production `ALLOWED_ORIGINS`
- [ ] Configure logging

See [deployment.md](deployment.md) for deployment options.
