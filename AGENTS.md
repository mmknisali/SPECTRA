# SPECTRA - Oncology Assistant

## System for Predictive Evaluation, Clinical Triage & Risk Assessment

This repository contains the code for a healthcare AI system built for a Turkish cancer patient dataset.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Process data
python -m backend.export_data

# 3. Train classifier
python -m backend.cancer_classifier

# 4. Run (two terminals)
python -m backend.api              # Terminal 1: API server
streamlit run frontend/app.py       # Terminal 2: UI
```

---

## Dataset

- **File**: `datamedx_veriset_26.xlsx`
- **Size**: 500 patients, 54 features
- **Language**: Turkish
- **Cancer Types**: Karaciğer kanseri, Meme Kanseri, Multipl miyelom, Over kanseri, Prostat kanseri (100 each)

### Key Columns Used

| Column | Description |
|--------|-------------|
| `kanser_turu` | Cancer type |
| `icd10` | ICD-10 codes |
| `ilac` | Medications |
| `epikriz` | Clinical notes |
| `hba1c`, `ast`, `alt`, etc. | Lab values |

---

## Architecture

```
┌──────────────────┐     ┌──────────────────┐
│  Streamlit UI     │────►│  FastAPI API     │
│  (Port 8501)     │     │  (Port 8000)     │
└──────────────────┘     └────────┬─────────┘
                                 │
              ┌─────────────────────┼─────────────────────┐
              ▼                                         ▼
    ┌──────────────────┐                    ┌──────────────────┐
    │  XGBoost         │                    │  ChromaDB        │
    │  Classifier     │                    │  Knowledge Base │
    └──────────────────┘                    └──────────────────┘
```

---

## Commands

### Data Processing

```bash
# Export training data
python -m backend.export_data

# Train XGBoost (CPU, ~1 minute)
python -m backend.cancer_classifier

# Train LoRA (requires cloud GPU, ~$0.15-0.20/hr)
accelerate launch train.py --model Qwen/Qwen2-1.8B --use_lora
```

### Running

```bash
# API server
python -m backend.api

# Web UI
streamlit run frontend/app.py

# With custom port
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

---

## Hardware Requirements

| Resource | Minimum | Notes |
|----------|---------|-------|
| RAM | 8GB | - |
| VRAM | 4GB | For Qwen2:1.8B inference |
| Storage | 10GB | Models + data |

---

## Project Structure

```
/spectra
├── .envrc                    # direnv auto-activation
├── devenv.nix                # devenv configuration
├── .gitignore               # Git ignore rules
├── backend/
│   ├── data_processor.py     # Data loading/processing
│   ├── export_data.py       # Export training data
│   ├── cancer_classifier.py # XGBoost model
│   └── api.py             # FastAPI server
├── frontend/
│   └── app.py            # Streamlit UI
├── scripts/
│   └── setup.sh          # Setup script
├── data/
│   ├── training_data.json   # 2000 Q&A pairs
│   ├── knowledge_base.json# ICD-10 codes
│   └── cleaned_patients.csv
├── models/
│   ├── cancer_classifier.joblib
│   ├── feature_scaler.joblib
│   └── label_encoder.joblib
├── docs/                   # Documentation
├── requirements.txt         # Dependencies
├── README.md
└── AGENTS.md              # This file
```

---

## Development

### Using devenv

```bash
devenv shell
```

### Using direnv

```bash
direnv allow .
```

### Manual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/predict/cancer` | POST | Predict cancer type |
| `/predict/icd10` | POST | Generate ICD-10 codes |
| `/recommend/treatment` | POST | Get treatment recommendations |

---

## Constraints

### Model Training

- **Full fine-tune**: Requires 12-16GB VRAM (not possible on consumer GPU)
- **LoRA fine-tune**: Requires ~6GB VRAM (use vast.ai cloud GPU ~$0.15-0.20/hr)
- **Inference**: Works on 4GB VRAM with Q4 quantization

### Data

- Training data: ~2000 Q&A pairs generated from 500 patients
- Knowledge base: 20 ICD-10 codes extracted from dataset

---

## Troubleshooting

### Module not found

```bash
export PYTHONPATH=/path/to/spectra:$PYTHONPATH
```

### Model not found

```bash
python -m backend.cancer_classifier
```

### Port in use

```bash
lsof -i :8000
kill $(lsof -t -i :8000)
```

---

## Files to Check First

1. `README.md` - Project overview
2. `docs/api.md` - API documentation
3. `docs/development.md` - Development guide
4. `docs/deployment.md` - Deployment guide

---

*Last updated: April 2026*