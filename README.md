# SPECTRA - Oncology Assistant

## System for Predictive Evaluation, Clinical Triage & Risk Assessment

A comprehensive AI-powered oncology assistant built for the Turkish healthcare system. SPECTRA uses machine learning and large language models to assist healthcare professionals in cancer diagnosis, ICD-10 coding, and treatment recommendations.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Quick Start](#quick-start)
5. [Project Structure](#project-structure)
6. [Dataset](#dataset)
7. [Architecture](#architecture)
8. [API Documentation](#api-documentation)
9. [Development](#development)
10. [Deployment](#deployment)
11. [License](#license)

---

## Overview

### What is SPECTRA?

SPECTRA is an AI-powered oncology decision support system designed to assist healthcare professionals in Turkey with:

- **Cancer Type Prediction**: Predict cancer type from patient lab values
- **ICD-10 Coding**: Auto-generate ICD-10 diagnostic codes from clinical notes
- **Treatment Recommendations**: Evidence-based treatment recommendations

### Purpose

This system was developed for a healthcare hackathon using a Turkish cancer patient dataset containing 500 patients with 54 features. The goal is to demonstrate how AI/ML can assist healthcare professionals in their daily workflow.

### Target Users

- Hospital oncologists
- Medical coders
- Healthcare administrators
- Healthcare AI researchers

---

## Features

### 1. Cancer Type Prediction

- **Input**: Patient lab values (HbA1c, AST, ALT, etc.)
- **Output**: Predicted cancer type with confidence score
- **Model**: XGBoost classifier
- **Classes**: Karaciğer kanseri, Meme Kanseri, Multipl miyelom, Over kanseri, Prostat kanseri

### 2. ICD-10 Code Generator

- **Input**: Clinical notes + cancer type
- **Output**: Suggested ICD-10 codes with descriptions
- **Model**: Knowledge-based retrieval + optional LLM
- **Coverage**: 20+ ICD-10 codes in knowledge base

### 3. Treatment Recommender

- **Input**: Cancer type + optional lab values
- **Output**: Medications, recommended labs, treatment protocols
- **Data**: Evidence-based treatment mapping

---

## Tech Stack

### Core Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| ML | XGBoost | 2.0+ |
| LLM | Qwen2:1.8B | + LoRA |
| RAG | ChromaDB | 0.5+ |
| API | FastAPI | 0.110+ |
| UI | Streamlit | 1.40+ |
| Hosting | Homelab | - |

### Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8GB | 16GB |
| VRAM | 4GB | 8GB |
| Storage | 10GB | 50GB |

### Cloud Services (Optional)

| Service | Purpose | Cost |
|---------|---------|------|
| vast.ai | GPU training | ~$0.15-0.20/hr |
| Cloudflare | Tunnel | Free |

---

## Quick Start

### Option 1: With direnv (Recommended)

```bash
# Auto-activates environment when entering directory
direnv allow .
```

### Option 2: With devenv

```bash
devenv shell
```

### Option 3: Manual

```bash
# Install dependencies
pip install -r requirements.txt

# Process data
python -m backend.export_data

# Train classifier
python -m backend.cancer_classifier

# Run (two terminals)
python -m backend.api              # Terminal 1: API server
streamlit run frontend/app.py       # Terminal 2: UI
```

### Option 4: With scripts

```bash
# Run setup script
bash scripts/setup.sh
```

### Data Processing

```bash
# Generate training data and knowledge base
python -m backend.export_data
```

### Train Classifier

```bash
# Train XGBoost classifier (CPU)
python -m backend.cancer_classifier
```

### Run Application

```bash
# Terminal 1 - Start API
python -m backend.api

# Terminal 2 - Start UI
streamlit run frontend/app.py
```

### Access

Open http://localhost:8501 in your browser.

---

## Project Structure

```
spectra/
├── .envrc                    # direnv auto-activation
├── devenv.nix                # devenv configuration
├── devenv.lock              # devenv lock file
├── .gitignore               # Git ignore rules
├── backend/
│   ├── data_processor.py      # Data loading & processing
│   ├── export_data.py        # Export training data
│   ├── cancer_classifier.py # XGBoost model
│   └── api.py              # FastAPI backend
├── frontend/
│   └── app.py              # Streamlit UI
├── scripts/
│   └── setup.sh           # Setup script
├── data/
│   ├── datamedx_veriset_26.xlsx  # Original dataset
│   ├── training_data.json       # Generated training pairs
│   ├── knowledge_base.json       # ICD-10 knowledge base
│   └── cleaned_patients.csv      # Processed patient data
├── models/
│   ├── cancer_classifier.joblib   # Trained XGBoost model
│   ├── feature_scaler.joblib   # Feature scaler
│   └── label_encoder.joblib    # Label encoder
├── tests/
│   ├── test_api.py
│   └── test_classifier.py
├── docs/
│   ├── api.md
│   ├── development.md
│   └── deployment.md
│   └── deployment.md
├── devenv.nix                # Devenv configuration
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project configuration
├── README.md               # This file
└── AGENTS.md              # Agent instructions
```

---

## Dataset

### Source

- **File**: `datamedx_veriset_26.xlsx`
- **Size**: 500 patients, 54 features
- **Language**: Turkish

### Cancer Types

| Type | Turkish | Count |
|------|---------|-------|
| Liver Cancer | Karaciğer kanseri | 100 |
| Breast Cancer | Meme Kanseri | 100 |
| Multiple Myeloma | Multipl miyelom | 100 |
| Ovarian Cancer | Over kanseri | 100 |
| Prostate Cancer | Prostat kanseri | 100 |

### Key Features

| Category | Features |
|----------|----------|
| Demographics | cinsiyet (gender), doğum tarihi (birth date) |
| Diagnosis | kanser_turu (cancer type), icd10 |
| Labs | hba1c, ast, alt, alp, ggt, bilirubin, üre, kreatinin, bun |
| Medications | ilac (medications) |
| Clinical | epikriz (clinical notes), department |

### Data Processing

The data processor performs:

1. **Cleaning**: Remove brackets, standardize text
2. **Extraction**: Parse ICD-10 codes, drug names
3. **Feature Engineering**: Calculate lab ratios
4. **Training Data Generation**: Create Q&A pairs

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                  │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Tab 1: Cancer Prediction                       │ │
│  │  Tab 2: ICD-10 Coder                            │ │
│  │  Tab 3: Treatment Recommender                 │ │
│  └─────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────┘
                            │ HTTP
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │ /predict/cancer   │  │ /predict/icd10    │              │
│  └──────────────────┘  └──────────────────┘              │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │ /recommend/treat │  │ /health           │              │
│  └──────────────────┘  └──────────────────┘              │
└───────────────────────────┬───────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                         ▼
┌─────────────────────┐    ┌─────────────────────┐
│   XGBoost Model      │    │  ChromaDB Knowledge  │
│   (Classification)  │    │  (RAG)               │
└─────────────────────┘    └─────────────────────┘
```

### Data Flow

1. **User Input**: User enters data via Streamlit UI
2. **API Request**: Frontend sends HTTP request to FastAPI
3. **Model Processing**: Backend loads models, processes input
4. **Prediction**: XGBoost/Knowledge base generates predictions
5. **Response**: API returns JSON response
6. **Display**: Frontend renders results

---

## API Documentation

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "models_loaded": true,
  "knowledge_base_size": 20
}
```

#### 2. Cancer Prediction

```
POST /predict/cancer
```

Request:
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

Response:
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

#### 3. ICD-10 Code Generation

```
POST /predict/icd10
```

Request:
```json
{
  "clinical_note": "Patient presents with liver mass, elevated AST/ALT",
  "cancer_type": "Karaciğer kanseri"
}
```

Response:
```json
{
  "suggested_codes": [
    {
      "code": "C22.0",
      "description": "Hepatocellüler karsinom",
      "score": 0.8,
      "cancer_types": ["Karaciğer kanseri"]
    }
  ],
  "source": "knowledge_base"
}
```

#### 4. Treatment Recommendation

```
POST /recommend/treatment
```

Request:
```json
{
  "cancer_type": "Karaciğer kanseri",
  "patient_labs": {
    "ast": 120.0,
    "alt": 85.0
  }
}
```

Response:
```json
{
  "cancer_type": "Karaciğer kanseri",
  "recommended_medications": ["Sorafenib", "Levatinib"],
  "recommended_labs": ["AST", "ALT", "AFP"],
  "protocols": ["Transarteriyel Kemoblokasyon"]
}
```

---

## Development

### Using devenv (Recommended)

```bash
devenv shell
```

### Using direnv (Auto-activate)

```bash
# Grant permission to direnv
direnv allow .

# Environment auto-activates when entering directory
cd /path/to/spectra
```

### Using nix-shell

```bash
nix-shell -p python3 python3Packages.pandas python3Packages.openpyxl \
  python3Packages.scikit-learn python3Packages.xgboost
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install vast CLI
pip install vastai
```

#### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_api.py
```

### Training Models

#### XGBoost Classifier

```bash
python -m backend.cancer_classifier
```

#### LoRA Fine-tuning (Requires Cloud GPU)

```bash
# On vast.ai or cloud GPU
accelerate launch train.py \
  --model_name_or_path Qwen/Qwen2-1.8B \
  --use_lora \
  --output_dir ./models/lora_adapter
```

---

## Deployment

### Local Deployment

```bash
# Start API
python -m backend.api

# Start UI (separate terminal)
streamlit run frontend/app.py
```

### Homelab Deployment

```bash
# Install on homelab
git clone <repo> /opt/spectra
cd /opt/spectra

# Install dependencies
pip install -r requirements.txt

# Train models
python -m backend.export_data
python -m backend.cancer_classifier

# Start services
python -m backend.api &
streamlit run frontend/app.py &

# Expose via Cloudflare Tunnel
cloudflare tunnel login
cloudflare tunnel create spectra
cloudflare tunnel config add --port 8501
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["python", "-m", "backend.api"]
```

---

## Known Limitations

### Model Performance

- **XGBoost Classifier**: 20% accuracy on lab values alone (expected - lab values not strong predictors)
- **Knowledge Base**: Limited to 20 ICD-10 codes from dataset
- **Treatment Recommendations**: Rule-based mapping, not ML-generated

### Hardware Constraints

- **LoRA Training**: Requires cloud GPU (~6GB VRAM for Qwen2:1.8B)
- **Inference**: Works on 4GB VRAM with Q4 quantization
- **Full Fine-tuning**: Not possible without 16GB+ VRAM

### Future Improvements

- [ ] Add more ICD-10 codes
- [ ] Implement LoRA fine-tuning
- [ ] Add more treatment protocols
- [ ] Integrate with hospital systems
- [ ] Add patient outcome prediction

---

## License

This project is for educational and demonstration purposes.

---

## Authors

- SPECTRA Team

---

## Acknowledgments

- Turkish cancer patient dataset
- Healthcare hackathon organizers
- Open source community

---

## Support

For issues and questions:

1. Check the documentation in `docs/`
2. Review the API output
3. Check the logs

---

*Last updated: April 2026*