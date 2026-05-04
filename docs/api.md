# API Documentation

## Base URL

| Environment | URL |
|-------------|-----|
| Local | http://localhost:8000 |

**Interactive Docs**: http://localhost:8000/docs

---

## Endpoints

### Root

```
GET /
```

**Response:**
```json
{
  "message": "SPECTRA API - Oncology Assistant"
}
```

---

### Health Check

```
GET /health
```

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

---

### ICD-10 Code Generator

```
POST /predict/icd10
```

**Request:**
```json
{
  "clinical_note": "Patient presents with liver mass, elevated AST/ALT",
  "cancer_type": "Karaciğer kanseri"
}
```

**Response:**
```json
{
  "suggested_codes": [
    {
      "code": "C22.0",
      "description": "Malignant neoplasm: Liver and intrahepatic bile ducts",
      "score": 0.8,
      "cancer_types": ["Karaciğer kanseri"]
    }
  ],
  "source": "knowledge_base"
}
```

---

### Treatment Recommender

```
POST /recommend/treatment
```

**Request:**
```json
{
  "cancer_type": "Karaciğer kanseri",
  "patient_labs": {
    "ast": 120,
    "alt": 95
  }
}
```

**Response:**
```json
{
  "cancer_type": "Karaciğer kanseri",
  "recommended_labs": ["AFP", "AST", "ALT", "Bilirubin", "Albumin"],
  "treatment_protocol": "Hepatosellüler karsinomda BCLC evreleme sistemine göre tedavi...",
  "source": "rag+llm"
}
```

---

## Error Responses

| Status | Description |
|--------|-------------|
| 500 | Internal server error |
| 503 | Service unavailable (e.g., knowledge base not loaded) |

---

## Rate Limiting

None (for local use)