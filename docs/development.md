# Development Guide

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Project Structure](#project-structure)
3. [Data Processing](#data-processing)
4. [Model Training](#model-training)
5. [Testing](#testing)
6. [Code Style](#code-style)

---

## Environment Setup

### Using devenv (Recommended)

```bash
# Enter environment
devenv shell
```

### Using direnv (Auto-activate)

```bash
# Grant permission to direnv
direnv allow .

# Environment auto-activates when entering directory
cd /path/to/spectra
```

### Using Nix-shell

```bash
# Enter development environment
nix-shell -p python3 python3Packages.pandas python3Packages.openpyxl python3Packages.scikit-learn python3Packages.xgboost
```

### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
pip install -r requirements.txt
```

---

## Project Structure

```
/spectra
├── .envrc                    # direnv auto-activation
├── devenv.nix                # devenv configuration
├── backend/
│   ├── data_processor.py     # Data loading and cleaning
│   ├── export_data.py       # Export training data
│   ├── cancer_classifier.py # XGBoost model
│   └── api.py              # FastAPI server
├── frontend/
│   └── app.py              # Streamlit UI
├── scripts/
│   └── setup.sh           # Setup script
├── data/                    # Data files
├── models/                  # Trained models
├── tests/                   # Test files
└── docs/                    # Documentation
```

### Backend Module

The `backend/` module contains:

| File | Purpose |
|------|---------|
| `data_processor.py` | Data loading and cleaning |
| `export_data.py` | Export training data |
| `cancer_classifier.py` | XGBoost model |
| `api.py` | FastAPI server |

### Data Flow

```
datamedx_veriset_26.xlsx
    │
    ▼ (load_dataset)
DataFrame
    │
    ▼ (process_patient)
Dict with:
  - cancer_type
  - icd10_codes
  - medications
  - lab_values
    │
    ▼ (create_training_pairs)
training_data.json
    │
    ▼ (train_model)
cancer_classifier.joblib
```

---

## Data Processing

### Loading Data

```python
from backend.data_processor import load_dataset

df = load_dataset()
print(f"Loaded {len(df)} patients")
```

### Processing Patients

```python
from backend.data_processor import process_patient

patient = process_patient(df.iloc[0])
print(patient['cancer_type'])
print(patient['icd10_codes'])
print(patient['medications'])
```

### Creating Training Pairs

```python
from backend.data_processor import create_training_pairs

training_pairs = create_training_pairs(df)
print(f"Created {len(training_pairs)} training pairs")
```

---

## Model Training

### XGBoost Classifier

```python
# Run the training script
python -m backend.cancer_classifier
```

Output:
```
Loading data...
Extracting features...
Encoding labels...
Classes: ['Karaciğer kanseri', 'Meme Kanseri', 'Multipl miyelom', 'Over kanseri', 'Prostat kanseri']
Splitting data...
Scaling features...
Training model...
Evaluating...
Test accuracy: 20.00%
Model saved to models/
```

### Training Options

| Parameter | Default | Description |
|------------|---------|-------------|
| `--n_estimators` | 200 | Number of trees |
| `--max_depth` | 4 | Maximum tree depth |
| `--learning_rate` | 0.1 | Learning rate |
| `--test_size` | 0.2 | Test set proportion |

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=backend
```

### Writing Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_predict_cancer():
    response = client.post("/predict/cancer", json={
        "hba1c": 5.5,
        "ast": 120.0,
        "alt": 85.0,
    })
    assert response.status_code == 200
    assert "cancer_type" in response.json()
```

---

## Code Style

### Python Conventions

- Use type hints where possible
- Use f-strings for string formatting
- Use 4 spaces for indentation
- Maximum line length: 100 characters

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Functions | snake_case | `process_patient` |
| Classes | PascalCase | `CancerClassifier` |
| Constants | UPPER_SNAKE_CASE | `MAX_ITERATIONS` |
| Variables | snake_case | `cancer_type` |

### Module Structure

```python
"""Module docstring"""

import os
from typing import Dict, List

# Constants
DEFAULT_PATH = "/data"

class MyClass:
    """Class docstring"""
    
    def __init__(self, param: str):
        self.param = param
    
    def process(self) -> Dict:
        """Process something"""
        return {"param": self.param}

def my_function(data: List[str]) -> str:
    """Function docstring"""
    return " ".join(data)
```

---

## Troubleshooting

### Common Issues

#### ImportError: No module named 'backend'

```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/spectra:$PYTHONPATH
```

#### Model not found

```bash
# Re-train the model
python -m backend.cancer_classifier
```

#### API not responding

```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
kill $(lsof -t -i :8000)
```

---

## Next Steps

- Add more test coverage
- Implement CI/CD
- Add type hints
- Document API endpoints