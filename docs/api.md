# API Documentation

Complete reference for the SPECTRA REST API.

---

## Base URL

| Environment | URL |
|-------------|-----|
| Local Development | http://localhost:8000 |
| Production | Set via environment |

**Interactive Documentation**: http://localhost:8000/docs (Swagger UI)

---

## Authentication

No authentication required for local use. For production, add authentication middleware in `backend/api.py`.

---

## Endpoints

### 1. Root — HTML Popup

```
GET /
```

Serves the diagnostic popup HTML page.

**Response:** HTML file (`text/html`)

**Status Codes:**
- `200` - Success

---

### 2. API Info

```
GET /api
```

Returns API information as JSON.

**Response:**
```json
{
  "message": "SPECTRA API - Oncology Assistant"
}
```

**Status Codes:**
- `200` - Success

---

### 3. Health Check

```
GET /health
```

Returns system status including knowledge base, ChromaDB, and Ollama availability.

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

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | System status: "healthy" or "degraded" |
| `knowledge_base_loaded` | boolean | Whether ICD-10 KB is loaded |
| `knowledge_base_size` | integer | Number of ICD-10 codes available |
| `chroma_ready` | boolean | Whether ChromaDB is accessible |
| `chroma_documents` | integer | Number of indexed patient records |
| `ollama_available` | boolean | Whether LLM is available |
| `ollama_models` | integer | Number of models loaded in Ollama |

**Status Codes:**
- `200` - Success

---

### 4. ICD-10 Code Generator

```
POST /predict/icd10
```

Generate ICD-10 diagnostic codes from clinical notes.

**Request Body:**
```json
{
  "clinical_note": "Patient presents with liver mass, elevated AST/ALT",
  "cancer_type": "Karaciğer kanseri"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `clinical_note` | string | Yes | Clinical notes text (max 10,000 chars) |
| `cancer_type` | string | No | Cancer type to filter results |

**Supported Cancer Types:**
- `Karaciğer kanseri`
- `Meme Kanseri`
- `Multipl miyelom`
- `Over kanseri`
- `Prostat kanseri`

**Response:**
```json
{
  "suggested_codes": [
    {
      "code": "C22.0",
      "description": "Malignant neoplasm: Liver and intrahepatic bile ducts",
      "score": 0.8,
      "cancer_types": ["Karaciğer kanseri"]
    },
    {
      "code": "C22.9",
      "description": "Malignant neoplasm of liver, primary, unspecified",
      "score": 0.5,
      "cancer_types": ["Karaciğer kanseri"]
    }
  ],
  "source": "knowledge_base"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `suggested_codes` | array | List of matching ICD-10 codes |
| `suggested_codes[].code` | string | ICD-10 code (e.g., "C22.0") |
| `suggested_codes[].description` | string | Code description |
| `suggested_codes[].score` | float | Relevance score (0.0 - 1.0) |
| `suggested_codes[].cancer_types` | array | Associated cancer types |
| `source` | string | Always "knowledge_base" |

**Scoring Algorithm:**
- +0.5 if cancer_type matches
- +0.3 if keywords in description match clinical note
- +0.5 if code prefix appears in clinical note
- Results sorted by score descending

**Status Codes:**
- `200` - Success
- `422` - Validation error (invalid request format)
- `503` - Knowledge base not loaded

---

### 5. Treatment Recommender

```
POST /recommend/treatment
```

Get evidence-based treatment recommendations using RAG + LLM (or fallback).

**Request Body:**
```json
{
  "cancer_type": "Karaciğer kanseri",
  "patient_labs": {
    "ast": 120,
    "alt": 95,
    "crp": 15,
    "albumin": 3.2
  }
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cancer_type` | string | Yes | Target cancer type |
| `patient_labs` | object | No | Patient laboratory values |

**Patient Labs Object:**
All lab values are optional. Supported fields:

| Field | Type | Description |
|-------|------|-------------|
| `hba1c` | float | Hemoglobin A1c |
| `üre` | float | Urea (mg/dL) |
| `kreatinin` | float | Creatinine (mg/dL) |
| `bun` | float | Blood Urea Nitrogen |
| `alt` | float | Alanine Aminotransferase (U/L) |
| `alp` | float | Alkaline Phosphatase (U/L) |
| `ast` | float | Aspartate Aminotransferase (U/L) |
| `ggt` | float | Gamma-Glutamyl Transferase (U/L) |
| `bilirubin` | float | Total Bilirubin (mg/dL) |
| `crp` | float | C-Reactive Protein (mg/L) |
| `ldh` | float | Lactate Dehydrogenase (U/L) |
| `albumin` | float | Serum Albumin (g/dL) |

**Response:**
```json
{
  "cancer_type": "Karaciğer kanseri",
  "recommended_labs": [
    "AFP",
    "AST",
    "ALT",
    "Bilirubin",
    "Albumin",
    "ALP",
    "GGT"
  ],
  "treatment_protocol": "Hepatosellüler karsinomda BCLC evreleme sistemine göre tedavi planlanır. Erken evre hastalarda cerrahi rezeksiyon veya ablasyon düşünülür. İleri evre hastalarda sistemik tedavi olarak tirozin kinaz inhibitörleri (Sorafenib, Lenvatinib) veya immünoterapi (Atezolizumab + Bevacizumab) kullanılır.",
  "source": "rag+llm"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `cancer_type` | string | Echo of requested cancer type |
| `recommended_labs` | array | List of recommended lab tests (Turkish) |
| `treatment_protocol` | string | Detailed treatment protocol (Turkish) |
| `source` | string | "rag+llm" or "fallback" |

**Source Values:**
- `"rag+llm"` - Generated using ChromaDB + Ollama LLM
- `"fallback"` - Hardcoded protocol (Ollama unavailable)

**Status Codes:**
- `200` - Success
- `422` - Validation error
- `500` - Internal error during recommendation generation

---

### 6. Clinical Summary Analyzer

```
POST /analyze/summary
```

Analyzes clinical text and optional lab results to produce a structured patient summary with cancer type, stage, treatment history, and key findings.

**Request Body:**
```json
{
  "clinical_text": "60-year-old female with right breast mass, diagnosed with invasive ductal carcinoma stage IIB. She received 4 cycles of AC chemotherapy followed by radiotherapy. Currently on letrozole. ECOG 1.",
  "lab_text": "Hb: 11.2, WBC: 4.5, Platelet: 250000, AST: 22, ALT: 18"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `clinical_text` | string | Yes | Clinical text to analyze (max 10,000 chars) |
| `lab_text` | string | No | Lab results text (free text) |

**Response:**
```json
{
  "cancer_type": "Meme Kanseri",
  "stage": "Evre IIB",
  "treatment_history": [
    "4 kür AC kemoterapi",
    "Radyoterapi"
  ],
  "current_medications": [
    "Letrozol"
  ],
  "key_findings": [
    "Sağ meme kitle",
    "İnvaziv duktal karsinom"
  ],
  "performance_status": "ECOG 1",
  "source": "rag+llm"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `cancer_type` | string | Identified cancer type |
| `stage` | string | Cancer stage extracted from text |
| `treatment_history` | array | List of past treatments |
| `current_medications` | array | List of current medications |
| `key_findings` | array | Key clinical findings |
| `performance_status` | string | ECOG or performance status |
| `source` | string | "rag+llm" or "fallback" |

**Status Codes:**
- `200` - Success
- `422` - Validation error
- `500` - Internal error during analysis

---

### 7. Risk Assessment Analyzer

```
POST /analyze/risk
```

Analyzes clinical text and lab results to produce a structured risk assessment including risk level, abnormal labs, metastasis indicators, and recommendations.

**Request Body:**
```json
{
  "clinical_text": "60-year-old female with right breast mass, diagnosed with invasive ductal carcinoma stage IIB. Patient has family history of breast cancer in mother and sister.",
  "lab_text": "Hb: 11.2, WBC: 4.5, CA 15-3: 45, CEA: 8.2, AST: 22, ALT: 18, ALP: 120"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `clinical_text` | string | Yes | Clinical text to analyze (max 10,000 chars) |
| `lab_text` | string | No | Lab results text (free text) |

**Response:**
```json
{
  "risk_level": "yüksek",
  "risk_factors": [
    "Aile öyküsü (anne ve kız kardeşte meme kanseri)",
    "İleri evre tanı (Evre IIB)"
  ],
  "abnormal_labs": [
    "CA 15-3: 45 (yüksek)",
    "CEA: 8.2 (yüksek)",
    "ALP: 120 (yüksek)"
  ],
  "metastasis_indicators": [
    "Yüksek ALP düzeyi kemik metastazı açısından değerlendirilmeli"
  ],
  "recommendations": [
    "Kemik sintigrafisi önerilir",
    "Genetik danışma (BRCA mutasyonu) önerilir"
  ],
  "source": "rag+llm"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `risk_level` | string | Risk level: "düşük", "orta", or "yüksek" |
| `risk_factors` | array | Identified risk factors |
| `abnormal_labs` | array | Abnormal lab values with interpretation |
| `metastasis_indicators` | array | Potential metastasis indicators |
| `recommendations` | array | Clinical recommendations |
| `source` | string | "rag+llm" or "fallback" |

**Status Codes:**
- `200` - Success
- `422` - Validation error
- `500` - Internal error during analysis

---

## Error Responses

All errors return JSON with detail message:

```json
{
  "detail": "Error description here"
}
```

**Status Codes:**
| Status | Description |
|--------|-------------|
| `400` | Bad request (malformed JSON) |
| `422` | Validation error (Pydantic validation failed) |
| `500` | Internal server error |
| `503` | Service unavailable (e.g., knowledge base not loaded) |

---

## Request/Response Models

### ICD10Request
```json
{
  "clinical_note": "string (max 10000 chars)",
  "cancer_type": "string (optional)"
}
```

### ICD10Response
```json
{
  "suggested_codes": [
    {
      "code": "string",
      "description": "string",
      "score": "number",
      "cancer_types": ["string"]
    }
  ],
  "source": "string"
}
```

### TreatmentRequest
```json
{
  "cancer_type": "string (required)",
  "patient_labs": {
    "hba1c": "number (optional)",
    "üre": "number (optional)",
    "kreatinin": "number (optional)",
    "bun": "number (optional)",
    "alt": "number (optional)",
    "alp": "number (optional)",
    "ast": "number (optional)",
    "ggt": "number (optional)",
    "bilirubin": "number (optional)",
    "crp": "number (optional)",
    "ldh": "number (optional)",
    "albumin": "number (optional)"
  }
}
```

### TreatmentResponse
```json
{
  "cancer_type": "string",
  "recommended_labs": ["string"],
  "treatment_protocol": "string",
  "source": "string"
}
```

### AnalyzeSummaryRequest
```json
{
  "clinical_text": "string (max 10000 chars)",
  "lab_text": "string (optional)"
}
```

### AnalyzeSummaryResponse
```json
{
  "cancer_type": "string",
  "stage": "string",
  "treatment_history": ["string"],
  "current_medications": ["string"],
  "key_findings": ["string"],
  "performance_status": "string",
  "source": "string"
}
```

### AnalyzeRiskRequest
```json
{
  "clinical_text": "string (max 10000 chars)",
  "lab_text": "string (optional)"
}
```

### AnalyzeRiskResponse
```json
{
  "risk_level": "string",
  "risk_factors": ["string"],
  "abnormal_labs": ["string"],
  "metastasis_indicators": ["string"],
  "recommendations": ["string"],
  "source": "string"
}
```

---

## Rate Limiting

No rate limiting for local use. For production deployment, add rate limiting middleware:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter

# Add to api.py
limiter = Limiter(key_func=lambda: "global")
app.state.limiter = limiter
```

---

## CORS

CORS is configured via `ALLOWED_ORIGINS` environment variable:

```bash
# Allow all origins (development)
ALLOWED_ORIGINS=*

# Specific origins (production)
ALLOWED_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

---

## Examples

### cURL Examples

**Root (HTML popup):**
```bash
curl http://localhost:8000/
```

**API Info:**
```bash
curl http://localhost:8000/api
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

**ICD-10 with Cancer Type:**
```bash
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "Meme Kanseri"}'
```

**ICD-10 with Clinical Note:**
```bash
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_note": "Patient has breast mass, family history of cancer",
    "cancer_type": "Meme Kanseri"
  }'
```

**Treatment with Labs:**
```bash
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{
    "cancer_type": "Multipl miyelom",
    "patient_labs": {
      "kreatinin": 2.1,
      "albumin": 2.8
    }
  }'
```

**Clinical Summary:**
```bash
curl -X POST http://localhost:8000/analyze/summary \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_text": "60-year-old female with right breast mass, invasive ductal carcinoma stage IIB. Received AC chemotherapy and radiotherapy. On letrozole. ECOG 1.",
    "lab_text": "Hb: 11.2, WBC: 4.5, AST: 22, ALT: 18"
  }'
```

**Risk Assessment:**
```bash
curl -X POST http://localhost:8000/analyze/risk \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_text": "60-year-old female with right breast mass, invasive ductal carcinoma stage IIB. Family history of breast cancer.",
    "lab_text": "Hb: 11.2, CA 15-3: 45, CEA: 8.2, ALP: 120"
  }'
```

### Python Examples

**Using requests:**
```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# ICD-10 prediction
response = requests.post(
    "http://localhost:8000/predict/icd10",
    json={
        "clinical_note": "Elevated liver enzymes, abdominal pain",
        "cancer_type": "Karaciğer kanseri"
    }
)
codes = response.json()["suggested_codes"]

# Treatment recommendation
response = requests.post(
    "http://localhost:8000/recommend/treatment",
    json={
        "cancer_type": "Prostat kanseri",
        "patient_labs": {"psa": 15.5}
    }
)
protocol = response.json()["treatment_protocol"]

# Clinical summary
response = requests.post(
    "http://localhost:8000/analyze/summary",
    json={
        "clinical_text": "60-year-old female with right breast mass, invasive ductal carcinoma stage IIB.",
        "lab_text": "Hb: 11.2, WBC: 4.5"
    }
)
summary = response.json()

# Risk assessment
response = requests.post(
    "http://localhost:8000/analyze/risk",
    json={
        "clinical_text": "60-year-old female with breast mass, family history of cancer.",
        "lab_text": "CA 15-3: 45, ALP: 120"
    }
)
risk = response.json()
```

**Using httpx (async):**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/predict/icd10",
        json={"cancer_type": "Over kanseri"}
    )
    codes = response.json()["suggested_codes"]
```

---

## Changelog

### v1.1.0
- Added `GET /` (HTML popup)
- Added `GET /api` (JSON API info)
- Added `POST /analyze/summary` (clinical summary analyzer)
- Added `POST /analyze/risk` (risk assessment analyzer)

### v1.0.0
- Initial release
- ICD-10 code prediction
- Treatment recommendations with RAG
- Fallback protocols for offline use
