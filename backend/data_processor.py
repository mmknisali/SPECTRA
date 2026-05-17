"""
Data Preprocessing Module
=========================
Loads, cleans, and structures the cancer patient dataset.
Supports Excel (.xlsx) and CSV (.csv) formats.

Pipeline:
    1. load_dataset() — read CSV or Excel
    2. process_patient() — extract structured fields from a row
    3. create_training_pairs() — build Q&A pairs for LoRA fine-tuning
    4. create_icd10_knowledge_base() — build ICD-10 → cancer_type mapping
    5. load_and_process() — orchestrates steps 1-4
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.config import DEFAULT_DATA_PATHS, LAB_EXTRACTION_PATTERNS, ML_LAB_COLUMNS
from backend.exceptions import DatasetNotFoundError
from backend.utils import (
    clean_string_column,
    extract_cancer_type,
    extract_drugs,
    extract_icd10_codes,
)


def load_dataset(path: Optional[str] = None) -> pd.DataFrame:
    """Load dataset from Excel or CSV (tries multiple fallback paths).

    Args:
        path: Specific path to dataset file, or None to try defaults.

    Returns:
        Loaded DataFrame.

    Raises:
        DatasetNotFoundError: If no dataset file is found.
    """
    paths_to_try = [path] if path else [str(p) for p in DEFAULT_DATA_PATHS]

    for p in paths_to_try:
        if os.path.exists(p):
            if p.endswith(".csv"):
                return pd.read_csv(p, low_memory=False)
            return pd.read_excel(p)

    raise DatasetNotFoundError(
        f"Dataset not found. Tried: {', '.join(paths_to_try)}. "
        "Place hackathon_veri.csv or datamedx_veriset_26.xlsx at the project root."
    )


def extract_lab_values(row: pd.Series) -> Dict[str, float]:
    """Extract numeric lab values from a patient row.

    First tries to get values from individual columns, then falls back to
    parsing the ``lab_sonuclari`` text field using centralized regex patterns.

    Args:
        row: Pandas Series representing a patient row.

    Returns:
        Dictionary of lab keys to float values.
    """
    labs: Dict[str, float] = {}

    # 1. Try individual lab columns first
    for col in ML_LAB_COLUMNS:
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                try:
                    labs[col] = float(val)
                except (ValueError, TypeError):
                    pass

    # 2. If no structured labs found, parse the text field
    if not labs and "lab_sonuclari" in row.index:
        lab_text = clean_string_column(row.get("lab_sonuclari", ""))
        text_lower = lab_text.lower()
        for pattern, display_name in LAB_EXTRACTION_PATTERNS:
            lab_key = display_name.lower()
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    labs[lab_key] = float(match.group(1))
                except ValueError:
                    pass

    return labs


def process_patient(row: pd.Series) -> Dict[str, Any]:
    """Process a single patient row into structured data.

    Args:
        row: Pandas Series representing a patient row.

    Returns:
        Dictionary with structured patient data.
    """
    # Try kanser_turu column first
    cancer_type = row.get("kanser_turu", "")

    # Fall back to extracting from clinical text fields
    if pd.isna(cancer_type) or not cancer_type:
        for field in ["epikriz", "hikaye", "patoloji rapor özet", "not"]:
            text = row.get(field, "")
            if pd.notna(text):
                extracted = extract_cancer_type(str(text))
                if extracted:
                    cancer_type = extracted
                    break

    # Extract and clean various fields
    icd10_raw = clean_string_column(row.get("icd10", ""))
    medications_raw = clean_string_column(row.get("ilac", ""))
    gender_raw = clean_string_column(row.get("cinsiyet", ""))
    department = clean_string_column(row.get("department", ""))
    epicrisis = clean_string_column(row.get("epikriz", ""))

    return {
        "cancer_type": cancer_type,
        "icd10_codes": extract_icd10_codes(icd10_raw),
        "icd10_raw": icd10_raw,
        "medications": extract_drugs(medications_raw),
        "gender": gender_raw,
        "department": department,
        "epicrisis": epicrisis[:500] if epicrisis else "",
        "lab_values": extract_lab_values(row),
    }


def create_training_pairs(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Create Q&A training pairs from patient data for LoRA fine-tuning.

    Args:
        df: DataFrame with patient data.

    Returns:
        List of training pairs with instruction/response format.
    """
    training_data: List[Dict[str, Any]] = []

    templates = [
        {
            "prompt": "{cancer} hastası için hangi ilaçlar kullanılır?",
            "format": lambda p: ", ".join(p["medications"][:10]) if p["medications"] else "Belirtilmemiş",
        },
        {
            "prompt": "{cancer} hastasında hangi lab değerleri takip edilmeli?",
            "format": lambda p: ", ".join(p["lab_values"].keys()),
        },
        {
            "prompt": "{cancer} için ICD-10 kodları nelerdir?",
            "format": lambda p: ", ".join(p["icd10_codes"][:5]) if p["icd10_codes"] else "Belirtilmemiş",
        },
        {
            "prompt": "{cancer} hastası hangi tedaviyi alır?",
            "format": lambda p: p["department"][:100] if p["department"] else "Medikal onkoloji",
        },
    ]

    for idx, row in df.iterrows():
        patient = process_patient(row)
        cancer = patient["cancer_type"]
        if not cancer:
            continue

        for template in templates:
            prompt = template["prompt"].format(cancer=cancer)
            response = template["format"](patient)

            training_data.append({
                "instruction": prompt,
                "response": response,
                "cancer_type": cancer,
                "patient_id": idx,
            })

    return training_data


def create_icd10_knowledge_base(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Create knowledge base from ICD-10 codes in the dataset.

    Args:
        df: DataFrame with patient data.

    Returns:
        List of knowledge base entries.
    """
    if "icd10" not in df.columns:
        return []

    knowledge: Dict[str, Dict[str, Any]] = {}

    for _, row in df.iterrows():
        raw = clean_string_column(row.get("icd10", ""))
        codes = extract_icd10_codes(raw)
        cancer = row.get("kanser_turu", "")

        for code in codes:
            if code not in knowledge:
                knowledge[code] = {
                    "code": code,
                    "cancer_types": set(),
                    "description": raw[:200],
                }
            knowledge[code]["cancer_types"].add(cancer)

    # Convert sets to lists for JSON serialization
    return [
        {
            "code": data["code"],
            "cancer_types": list(data["cancer_types"]),
            "description": data["description"],
        }
        for data in knowledge.values()
    ]


def load_and_process() -> Tuple[pd.DataFrame, List[Dict], List[Dict]]:
    """Main function to load and process all data.

    Returns:
        Tuple of (DataFrame, training_pairs, knowledge_base).
    """
    print("Loading dataset...")
    df = load_dataset()
    print(f"Loaded {len(df)} patients")

    has_cancer_col = "kanser_turu" in df.columns
    if not has_cancer_col:
        print("  (no 'kanser_turu' column — extracting from clinical notes)")

    print("Creating training pairs...")
    training_pairs = create_training_pairs(df)
    print(f"  Found {len(training_pairs)} training pairs")

    print("Creating ICD-10 knowledge base...")
    knowledge_base = create_icd10_knowledge_base(df)
    print(f"  Found {len(knowledge_base)} ICD-10 codes")

    return df, training_pairs, knowledge_base


if __name__ == "__main__":
    df, training, knowledge = load_and_process()
    print(f"\nTraining pairs: {len(training)}")
    print(f"ICD-10 codes: {len(knowledge)}")
