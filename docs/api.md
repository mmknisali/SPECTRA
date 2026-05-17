# API Documentation

## Base URL

| Environment | URL |
|-------------|-----|
| Local | http://localhost:8000 |
| Production | https://yourdomain.com |

Interactive docs: http://localhost:8000/docs

## Endpoints

### GET /

Serves the frontend popup HTML.

**Response:** `text/html`

### GET /api

Returns API information.

**Response:**
```json
{
  "name": "SPECTRA API",
  "version": "1.1.0",
  "description": "Oncology Assistant — ICD-10 Coding, Patient Summary & Risk Assessment",
  "endpoints": {
    "GET /": "Frontend popup UI",
    "GET /api": "API information",
    "GET /health": "System status",
    "POST /predict/icd10": "ICD-10 code prediction",
    "POST /recommend/treatment": "Treatment recommendation",
    "POST /analyze/summary": "Patient summary extraction",
    "POST /analyze/risk": "Risk assessment"
  }
}
```

### GET /health

Returns system health status.

**Response:**
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

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"healthy"` or `"degraded"` |
| `knowledge_base_loaded` | boolean | Whether ICD-10 KB is loaded |
| `knowledge_base_size` | integer | Number of ICD-10 codes |
| `chroma_ready` | boolean | Whether ChromaDB is accessible |
| `chroma_documents` | integer | Number of indexed patient records |
| `ollama_available` | boolean | Whether LLM is available |
| `ollama_models` | integer | Number of Ollama models loaded |

### POST /predict/icd10

Generate ICD-10 diagnostic codes from clinical notes.

**Request:**
```json
{
  "clinical_note": "Patient presents with breast mass, family history",
  "cancer_type": "Meme Kanseri"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `clinical_note` | string | Yes | Clinical notes (max 10,000 chars) |
| `cancer_type` | string | No | Cancer type to filter results |

**Response:**
```json
{
  "suggested_codes": [
    {
      "code": "C50.9",
      "description": "Malignant neoplasm of breast, unspecified",
      "score": 1.3,
      "cancer_types": ["Meme Kanseri"]
    }
  ],
  "source": "knowledge_base"
}
```

**Scoring:**
- +0.5 if `cancer_type` matches entry
- +0.3 if search terms appear in description
- +0.5 if code prefix appears in note

**Status Codes:**
- `200` — Success
- `422` — Validation error
- `503` — Knowledge base not loaded

### POST /recommend/treatment

Get treatment recommendations (RAG + LLM or fallback).

**Request:**
```json
{
  "cancer_type": "Meme Kanseri",
  "patient_labs": {
    "ast": 120,
    "alt": 95,
    "albumin": 3.2
  }
}
```

**Response:**
```json
{
  "cancer_type": "Meme Kanseri",
  "recommended_labs": ["CEA", "CA 15-3", "Tam kan sayımı"],
  "treatment_protocol": "Meme kanserinde tedavi evreye göre planlanır...",
  "source": "rag+llm"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `cancer_type` | string | Echo of requested cancer type |
| `recommended_labs` | string[] | Recommended lab tests (Turkish) |
| `treatment_protocol` | string | Detailed protocol (Turkish) |
| `source` | string | `"rag+llm"` or `"fallback"` |

### POST /analyze/summary

Extract structured patient summary from clinical text.

**Request:**
```json
{
  "clinical_text": "60 yaşında meme kanseri hastası, opere, kemoterapi alıyor. ECOG 1.",
  "lab_text": "Hb: 11.2, WBC: 4.5, AST: 22"
}
```

**Response:**
```json
{
  "cancer_type": "Meme Kanseri",
  "stage": "Belirtilmemiş",
  "treatment_history": ["Cerrahi geçirmiş", "Kemoterapi almış"],
  "current_medications": [],
  "key_findings": ["60 yaşında meme kanseri hastası..."],
  "performance_status": "ECOG 1",
  "source": "rag+llm"
}
```

### POST /analyze/risk

Generate risk assessment from clinical text and labs.

**Request:**
```json
{
  "clinical_text": "Metastatik meme kanseri, karaciğer metastazı",
  "lab_text": "AST: 120, ALT: 95, CRP: 15"
}
```

**Response:**
```json
{
  "risk_level": "yüksek",
  "risk_factors": ["Metastaz varlığı", "İleri evre hastalık"],
  "abnormal_labs": ["AST: 120 (YÜKSEK, normal: 0-40)", "ALT: 95 (YÜKSEK, normal: 0-40)", "CRP: 15 (YÜKSEK, normal: 0-5)"],
  "metastasis_indicators": ["karaciğer metastazı"],
  "recommendations": [
    "Hasta yakın takip önerilir.",
    "Multidisipliner onkoloji konseyinde değerlendirilmesi önerilir."
  ],
  "source": "rag+llm"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `risk_level` | string | `"düşük"`, `"orta"`, or `"yüksek"` |
| `risk_factors` | string[] | Identified risk factors |
| `abnormal_labs` | string[] | Abnormal lab values with interpretation |
| `metastasis_indicators` | string[] | Potential metastasis indicators |
| `recommendations` | string[] | Clinical recommendations |
| `source` | string | `"rag+llm"` or `"fallback"` |

## Error Responses

All errors return:
```json
{
  "detail": "Error description"
}
```

| Status | Description |
|--------|-------------|
| `422` | Validation error (Pydantic) |
| `500` | Internal server error |
| `503` | Service unavailable (KB not loaded) |

## Examples

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Risk assessment
curl -X POST http://localhost:8000/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "Metastatik meme kanseri", "lab_text": "AST: 120"}'

# Patient summary
curl -X POST http://localhost:8000/analyze/summary \
  -H "Content-Type: application/json" \
  -d '{"clinical_text": "60 yaşında meme kanseri hastası"}'

# ICD-10 prediction
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "meme kanseri", "cancer_type": "Meme Kanseri"}'
```

### Python

```python
import requests

BASE = "http://localhost:8000"

# Health check
health = requests.get(f"{BASE}/health").json()

# Risk assessment
risk = requests.post(f"{BASE}/analyze/risk", json={
    "clinical_text": "Metastatik meme kanseri",
    "lab_text": "AST: 120, ALT: 95",
}).json()

# Patient summary
summary = requests.post(f"{BASE}/analyze/summary", json={
    "clinical_text": "60 yaşında meme kanseri hastası, opere",
}).json()

# ICD-10 prediction
codes = requests.post(f"{BASE}/predict/icd10", json={
    "clinical_note": "meme kanseri tanısı",
    "cancer_type": "Meme Kanseri",
}).json()
```
