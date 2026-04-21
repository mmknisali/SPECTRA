# API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [Endpoints](#endpoints)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Examples](#examples)

---

## Overview

The SPECTRA API provides programmatic access to the oncology assistant features. It is built using FastAPI and provides a RESTful interface.

### API Version

- **Current Version**: 1.0.0
- **Base URL**: `http://localhost:8000`

---

## Base URL

| Environment | URL |
|--------------|-----|
| Development | http://localhost:8000 |
| Production | http://your-domain.com |

### Interactive Documentation

FastAPI provides interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Authentication

Currently, no authentication is required for local development. For production deployment, consider adding API key authentication.

---

## Endpoints

### 1. Root

```
GET /
```

Returns API information.

**Response:**
```json
{
  "message": "SPECTRA API - Oncology Assistant"
}
```

---

### 2. Health Check

```
GET /health
```

Returns API health status and loaded components.

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": true,
  "knowledge_base_size": 20
}
```

| Field | Type | Description |
|-------|------|-------------|
| status | string | Health status ("healthy" or "unhealthy") |
| models_loaded | boolean | Whether ML models are loaded |
| knowledge_base_size | int | Number of ICD-10 codes in knowledge base |

---

### 3. Cancer Prediction

```
POST /predict/cancer
```

Predict cancer type from patient lab values.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| hba1c | float | No | HbA1c percentage |
| üre | float | No | Üre (mg/dL) |
| kreatinin | float | No | Kreatinin (mg/dL) |
| bun | float | No | BUN (mg/dL) |
| alt | float | No | ALT (U/L) |
| alp | float | No | ALP (U/L) |
| ast | float | No | AST (U/L) |
| ggt | float | No | GGT (U/L) |
| bilirubin | float | No | Bilirubin (mg/dL) |
| potasyum | float | No | Potasyum (mEq/L) |
| kalsiyum | float | No | Kalsiyum (mg/dL) |
| magnezyum | float | No | Magnezyum (mg/dL) |
| klor | float | No | Klor (mEq/L) |
| albumin | float | No | Albumin (g/dL) |
| crp | float | No | CRP (mg/L) |
| ldh | float | No | LDH (U/L) |
| sodyum | float | No | Sodyum (mEq/L) |

**Example Request:**
```json
{
  "hba1c": 5.5,
  "ast": 120.0,
  "alt": 85.0,
  "alp": 150.0,
  "ggt": 50.0,
  "bilirubin": 1.5,
  "üre": 20.0,
  "kreatinin": 1.0,
  "bun": 15.0,
  "crp": 10.0,
  "ldh": 250.0,
  "albumin": 4.0
}
```

**Response:**

```json
{
  "cancer_type": "Karaciğer kanseri",
  "confidence": 0.85,
  "all_predictions": {
    "Karaciğer kanseri": 0.85,
    "Meme Kanseri": 0.05,
    "Multipl miyelom": 0.03,
    "Over kanseri": 0.02,
    "Prostat kanseri": 0.05
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| cancer_type | string | Predicted cancer type |
| confidence | float | Confidence score (0-1) |
| all_predictions | object | Predictions for all cancer types |

---

### 4. ICD-10 Prediction

```
POST /predict/icd10
```

Generate ICD-10 codes from clinical notes.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| clinical_note | string | Yes | Clinical notes text |
| cancer_type | string | No | Known or suspected cancer type |

**Example Request:**
```json
{
  "clinical_note": "Patient presents with liver mass, elevated AST/ALT, AFP elevated",
  "cancer_type": "Karaciğer kanseri"
}
```

**Response:**

```json
{
  "suggested_codes": [
    {
      "code": "C22.0",
      "description": "Hepatocellüler karsinom",
      "score": 0.8,
      "cancer_types": ["Karaciğer kanseri"]
    },
    {
      "code": "C22.9",
      "description": "Karaciğer malign neoplazmı, tanımlanmamış",
      "score": 0.5,
      "cancer_types": ["Karaciğer kanseri"]
    }
  ],
  "source": "knowledge_base"
}
```

| Field | Type | Description |
|-------|------|-------------|
| suggested_codes | array | Array of suggested ICD-10 codes |
| code | string | ICD-10 code |
| description | string | Code description |
| score | float | Relevance score (0-1) |
| cancer_types | array | Associated cancer types |
| source | string | Data source ("knowledge_base") |

---

### 5. Treatment Recommendation

```
POST /recommend/treatment
```

Get treatment recommendations for cancer type.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cancer_type | string | Yes | Cancer type |
| patient_labs | object | No | Patient lab values |

**Example Request:**
```json
{
  "cancer_type": "Karaciğer kanseri",
  "patient_labs": {
    "ast": 120.0,
    "alt": 85.0,
    "crp": 10.0
  }
}
```

**Response:**

```json
{
  "cancer_type": "Karaciğer kanseri",
  "recommended_medications": [
    "Sorafenib",
    "Levatinib",
    "Atezolizumab",
    "Bevacizumab"
  ],
  "recommended_labs": [
    "AST",
    "ALT",
    "AFP",
    "Alp"
  ],
  "protocols": [
    "Transarteriyel Kemoblokasyon",
    "Radyoablasyon",
    "Cerrahi rezeksiyon"
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| cancer_type | string | Input cancer type |
| recommended_medications | array | Recommended medications |
| recommended_labs | array | Recommended lab tests |
| protocols | array | Treatment protocols |

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found |
| 422 | Validation Error |
| 503 | Service Unavailable - Models not loaded |
| 500 | Internal Server Error |

### Error Examples

#### 400 - Missing Required Field

```json
{
  "detail": "Field 'clinical_note' is required"
}
```

#### 503 - Models Not Loaded

```json
{
  "detail": "Models not loaded"
}
```

---

## Rate Limiting

Rate limiting is not currently enabled. For production, consider adding rate limiting middleware.

---

## Examples

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Cancer prediction
curl -X POST http://localhost:8000/predict/cancer \
  -H "Content-Type: application/json" \
  -d '{"hba1c": 5.5, "ast": 120.0, "alt": 85.0}'

# ICD-10 prediction
curl -X POST http://localhost:8000/predict/icd10 \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "Liver mass", "cancer_type": "Karaciğer kanseri"}'

# Treatment recommendation
curl -X POST http://localhost:8000/recommend/treatment \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "Karaciğer kanseri"}'
```

### Using Python

```python
import requests

API_BASE = "http://localhost:8000"

# Cancer prediction
response = requests.post(f"{API_BASE}/predict/cancer", json={
    "hba1c": 5.5,
    "ast": 120.0,
    "alt": 85.0,
})
print(response.json())

# ICD-10 prediction
response = requests.post(f"{API_BASE}/predict/icd10", json={
    "clinical_note": "Liver mass",
    "cancer_type": "Karaciğer kanseri"
})
print(response.json())

# Treatment recommendation
response = requests.post(f"{API_BASE}/recommend/treatment", json={
    "cancer_type": "Karaciğer kanseri"
})
print(response.json())
```

### Using JavaScript

```javascript
const API_BASE = "http://localhost:8000";

// Cancer prediction
const response = await fetch(`${API_BASE}/predict/cancer`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    hba1c: 5.5,
    ast: 120.0,
    alt: 85.0
  })
});
const data = await response.json();
console.log(data);
```

---

## Changelog

### v1.0.0 (2026-04-21)

- Initial release
- Cancer type prediction endpoint
- ICD-10 code generation endpoint
- Treatment recommendation endpoint