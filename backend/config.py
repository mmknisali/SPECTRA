"""
SPECTRA Configuration Module
============================
Centralizes all configuration settings, environment variables, and constants.

This module is the single source of truth for:
- Project paths and directories
- Ollama/LLM configuration
- API settings and limits
- Cancer type keywords for extraction
- ICD-10 code mappings
- Laboratory reference ranges
- Lab extraction regex patterns
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
OUTPUT_DIR = DATA_DIR
CHROMA_PATH = DATA_DIR / "chroma"

# ---------------------------------------------------------------------------
# Default data file paths (in order of preference)
# ---------------------------------------------------------------------------
DEFAULT_DATA_PATHS: List[Path] = [
    ROOT_DIR / "hackathon_veri.csv",
    ROOT_DIR / "datamedx_veriset_26.xlsx",
]

# ---------------------------------------------------------------------------
# ChromaDB configuration
# ---------------------------------------------------------------------------
COLLECTION_NAME = "spectra_knowledge"

# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:7b-instruct-q5_K_M")
OLLAMA_TIMEOUT = 120  # seconds

# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
MAX_CLINICAL_NOTE_LENGTH = 10000  # characters
DEFAULT_API_PORT = 8000

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
USE_LLM_FALLBACK = True  # Always use fallback if LLM fails
ENABLE_CHROMADB = True

# ---------------------------------------------------------------------------
# Cancer type keywords for extraction
# Format: (list_of_keywords, canonical_name)
# Order matters: first match wins.
# ---------------------------------------------------------------------------
CANCER_KEYWORDS: List[Tuple[List[str], str]] = [
    (["meme kanseri", "meme karsinomu", "meme ca", "meme malign", "meme tümörü"], "Meme Kanseri"),
    (["karaciğer kanseri", "karaciğer karsinomu", "hepatosellüler", "hcc", "hepatom"], "Karaciğer kanseri"),
    (["multipl miyelom", "multiple myelom", "plazma hücreli"], "Multipl miyelom"),
    (["over kanseri", "over karsinomu", "over ca", "yumurtalık kanseri"], "Over kanseri"),
    (["prostat kanseri", "prostat karsinomu", "prostat ca"], "Prostat kanseri"),
    (["akciğer kanseri", "akciğer karsinomu", "akciğer ca", "lung cancer", "küçük hücreli"], "Akciğer kanseri"),
    (["kolon kanseri", "kolon karsinomu", "kolorektal", "rektum kanseri", "bağırsak kanseri"], "Kolon kanseri"),
    (["pankreas kanseri", "pankreas karsinomu", "pankreas ca"], "Pankreas kanseri"),
    (["mide kanseri", "mide karsinomu", "gastric", "gastrik"], "Mide kanseri"),
    (["mesane kanseri", "mesane ca", "bladder"], "Mesane kanseri"),
    (["böbrek kanseri", "böbrek karsinomu", "renal hücre"], "Böbrek kanseri"),
    (["lenfoma", "hodgkin", "non-hodgkin"], "Lenfoma"),
    (["lösemi"], "Lösemi"),
    (["tiroid kanseri", "tiroid karsinomu", "tiroid ca"], "Tiroid kanseri"),
    (["baş boyun kanseri", "baş boyun"], "Baş boyun kanseri"),
    (["endometriyum kanseri", "endometrium", "rahim kanseri", "uterus"], "Endometriyum kanseri"),
    (["serviks kanseri", "serviks", "rahim ağzı"], "Serviks kanseri"),
    (["malign melanom", "melanom", "melanoma"], "Malign melanom"),
]

# ---------------------------------------------------------------------------
# ICD-10 to cancer type mapping
# ---------------------------------------------------------------------------
ICD10_CANCER_MAPPING: Dict[str, str] = {
    "C22": "Karaciğer kanseri",
    "C22.0": "Karaciğer kanseri",
    "C22.9": "Karaciğer kanseri",
    "C50": "Meme Kanseri",
    "C50.9": "Meme Kanseri",
    "C56": "Over kanseri",
    "C56.9": "Over kanseri",
    "C61": "Prostat kanseri",
    "C90": "Multipl miyelom",
}

# ---------------------------------------------------------------------------
# Lab test reference ranges (min, max)
# ---------------------------------------------------------------------------
LAB_REFERENCE_RANGES: Dict[str, Tuple[float, float]] = {
    "AST": (0, 40),
    "ALT": (0, 40),
    "CRP": (0, 5),
    "Kreatinin": (0.5, 1.2),
    "Üre": (10, 50),
    "Sodyum": (135, 145),
    "Potasyum": (3.5, 5.5),
    "Kalsiyum": (8.5, 10.5),
    "Albumin": (3.5, 5.0),
    "Bilirubin": (0, 1.2),
    "GGT": (0, 55),
    "LDH": (0, 250),
    "HbA1c": (4, 6),
    "HGB": (12, 18),
    "WBC": (4, 11),
    "PLT": (150, 450),
}

# ---------------------------------------------------------------------------
# Lab columns used in ML classifier (must match CSV column names)
# ---------------------------------------------------------------------------
ML_LAB_COLUMNS: List[str] = [
    "hba1c", "üre", "kreatinin", "bun", "alt", "alp", "ast", "ggt",
    "bilirubin", "potasyum", "kalsiyum", "magnezyum", "klor",
    "albumin", "crp", "ldh", "sodyum",
]

# ---------------------------------------------------------------------------
# Lab extraction patterns for text parsing
# Format: (regex_pattern, display_name)
# Patterns are matched case-insensitively against lab text.
# ---------------------------------------------------------------------------
LAB_EXTRACTION_PATTERNS: List[Tuple[str, str]] = [
    (r"ast[:\s]*([\d.]+)", "AST"),
    (r"alt[:\s]*([\d.]+)", "ALT"),
    (r"crp[:\s]*([\d.]+)", "CRP"),
    (r"kreatinin[:\s]*([\d.]+)", "Kreatinin"),
    (r"üre[:\s]*([\d.]+)", "Üre"),
    (r"sodyum[:\s]*([\d.]+)", "Sodyum"),
    (r"potasyum[:\s]*([\d.]+)", "Potasyum"),
    (r"kalsiyum[:\s]*([\d.]+)", "Kalsiyum"),
    (r"albumin[:\s]*([\d.]+)", "Albumin"),
    (r"bilirubin[:\s]*([\d.]+)", "Bilirubin"),
    (r"ggt[:\s]*([\d.]+)", "GGT"),
    (r"ldh[:\s]*([\d.]+)", "LDH"),
    (r"hba1c[:\s]*([\d.]+)", "HbA1c"),
    (r"hgb[:\s]*([\d.]+)", "HGB"),
    (r"wbc[:\s]*([\d.]+)", "WBC"),
    (r"plt[:\s]*([\d.]+)", "PLT"),
]
