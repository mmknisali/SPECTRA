"""
SPECTRA Utility Functions
=========================
Shared helper functions for text processing, data extraction, and calculations.

All functions are pure (no side effects) and use constants from config.py.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import (
    CANCER_KEYWORDS,
    ICD10_CANCER_MAPPING,
    LAB_EXTRACTION_PATTERNS,
    LAB_REFERENCE_RANGES,
)


def extract_cancer_type(text: str) -> Optional[str]:
    """Extract cancer type from clinical text using keyword matching.

    Args:
        text: Clinical text to analyze.

    Returns:
        Canonical cancer type name or None if not found.
    """
    if not text:
        return None

    text_lower = text.lower()
    for keywords, cancer_name in CANCER_KEYWORDS:
        for kw in keywords:
            if kw in text_lower:
                return cancer_name
    return None


def extract_cancer_from_text(text: str) -> Optional[str]:
    """Alias for extract_cancer_type (backward compatibility)."""
    return extract_cancer_type(text)


def get_primary_cancer_type(icd10_codes: List[str]) -> Optional[str]:
    """Map the first matching ICD-10 code to a cancer type.

    Args:
        icd10_codes: List of ICD-10 codes.

    Returns:
        Cancer type name or None if no match.
    """
    for code in icd10_codes:
        if code in ICD10_CANCER_MAPPING:
            return ICD10_CANCER_MAPPING[code]
    return None


def extract_icd10_codes(icd10_string: str) -> List[str]:
    """Extract individual ICD-10 codes from a combined string.

    Args:
        icd10_string: String containing ICD-10 codes.

    Returns:
        List of unique ICD-10 codes.
    """
    if not icd10_string:
        return []
    codes = re.findall(r"([A-Z]\d+\.?\d*)", icd10_string)
    return list(set(codes))


def extract_drugs(medication_string: str) -> List[str]:
    """Extract individual drug names from a bracket-delimited medication string.

    Args:
        medication_string: String containing drug names in brackets,
            e.g. "[Tamoksifen] [Letrozol]".

    Returns:
        List of unique drug names.
    """
    if not medication_string:
        return []
    drugs = re.findall(r"\[([^\]]+)\]", medication_string)
    return list(set(d.strip() for d in drugs))


def extract_labs_from_text(lab_text: str) -> Dict[str, str]:
    """Extract lab name/value pairs from free text.

    Args:
        lab_text: Text containing lab results.

    Returns:
        Dictionary mapping lab display names to their string values.
    """
    if not lab_text:
        return {}

    labs: Dict[str, str] = {}
    text_lower = lab_text.lower()

    for pattern, name in LAB_EXTRACTION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            labs[name] = match.group(1)

    return labs


def flag_abnormal_labs(labs: Dict[str, str]) -> List[str]:
    """Flag lab values outside reference ranges.

    Args:
        labs: Dictionary mapping lab names to string values.

    Returns:
        List of human-readable abnormality descriptions.
    """
    flags: List[str] = []

    for name, val_str in labs.items():
        try:
            val = float(val_str)
        except ValueError:
            continue

        if name not in LAB_REFERENCE_RANGES:
            continue

        lo, hi = LAB_REFERENCE_RANGES[name]
        if val < lo:
            flags.append(f"{name}: {val_str} (DÜŞÜK, normal: {lo}-{hi})")
        elif val > hi:
            flags.append(f"{name}: {val_str} (YÜKSEK, normal: {lo}-{hi})")

    return flags


def clean_string_column(value: Any) -> str:
    """Clean a value by removing brackets, quotes, and excess whitespace.

    Args:
        value: Value to clean (any type).

    Returns:
        Cleaned string.
    """
    import pandas as pd

    if pd.isna(value):
        return ""

    text = str(value)
    text = re.sub(r"^\[|\]$", "", text)  # surrounding brackets
    text = re.sub(r"'", "", text)         # single quotes
    text = re.sub(r"\s+", " ", text)      # normalize whitespace
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length, appending a suffix if truncated.

    Args:
        text: Text to truncate.
        max_length: Maximum allowed length (including suffix).
        suffix: Suffix appended when truncation occurs.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def calculate_risk_score(
    risk_factors: List[str],
    abnormal_labs: List[str],
    metastasis_indicators: List[str],
) -> Tuple[str, int]:
    """Calculate overall risk level from indicator counts.

    Args:
        risk_factors: List of identified risk factors.
        abnormal_labs: List of abnormal lab flags.
        metastasis_indicators: List of metastasis indicators.

    Returns:
        Tuple of (risk_level, total_score).
        risk_level is one of: "düşük", "orta", "yüksek".
    """
    score = len(risk_factors) + len(abnormal_labs) + len(metastasis_indicators)

    if score >= 4:
        level = "yüksek"
    elif score >= 2:
        level = "orta"
    else:
        level = "düşük"

    return level, score
