"""
Export Pipeline
===============
Generates all data files needed by the SPECTRA API:

    data/training_data.json     — Q&A pairs for LoRA fine-tuning
    data/knowledge_base.json    — ICD-10 code → cancer_type mappings
    data/cleaned_patients.csv   — Structured patient data
    data/chroma/                — ChromaDB vector index for RAG

Usage:
    python -m backend.export_data
"""

import json
from pathlib import Path
from typing import List

import pandas as pd

from backend.config import DATA_DIR, OUTPUT_DIR
from backend.data_processor import load_and_process, process_patient
from backend.rag_engine import index_patient_data


def export_training_data(training_pairs: List[dict]) -> Path:
    """Export training pairs as JSON."""
    output_path = OUTPUT_DIR / "training_data.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(training_pairs, fh, ensure_ascii=False, indent=2)
    print(f"Exported {len(training_pairs)} training pairs to {output_path}")
    return output_path


def export_knowledge_base(knowledge_base: List[dict]) -> Path:
    """Export knowledge base as JSON."""
    output_path = OUTPUT_DIR / "knowledge_base.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(knowledge_base, fh, ensure_ascii=False, indent=2)
    print(f"Exported {len(knowledge_base)} knowledge entries to {output_path}")
    return output_path


def export_cleaned_data(df: pd.DataFrame) -> Path:
    """Export processed patient data as CSV."""
    processed = []
    for idx, row in df.iterrows():
        patient = process_patient(row)
        patient["patient_id"] = idx
        processed.append(patient)

    output_df = pd.DataFrame(processed)
    output_path = OUTPUT_DIR / "cleaned_patients.csv"
    output_df.to_csv(output_path, index=False)
    print(f"Exported {len(processed)} patients to {output_path}")
    return output_path


def index_chromadb(df: pd.DataFrame) -> int:
    """Index patient data into ChromaDB for RAG."""
    print("\nIndexing ChromaDB (for RAG-based analysis)...")
    count = index_patient_data(df)
    print(f"  Indexed {count} patient documents")
    return count


def main():
    """Export all data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading and processing data...")
    df, training, knowledge = load_and_process()

    print("\nExporting data files...")
    export_training_data(training)
    export_knowledge_base(knowledge)
    export_cleaned_data(df)

    print("\nIndexing vector database...")
    index_chromadb(df)

    print("\nDone! Files created in data/ directory:")
    print("  - training_data.json")
    print("  - knowledge_base.json")
    print("  - cleaned_patients.csv")
    print("  - chroma/ (vector database for RAG)")


if __name__ == "__main__":
    main()
