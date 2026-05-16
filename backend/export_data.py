"""
Export processed data for training and knowledge base
Run this script to generate training data files
"""

import json
import pandas as pd
from pathlib import Path
from .data_processor import load_and_process, process_patient

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR


def export_training_data(training_pairs):
    """Export training pairs as JSON"""
    output_path = OUTPUT_DIR / "training_data.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(training_pairs, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(training_pairs)} training pairs to {output_path}")
    return output_path


def export_knowledge_base(knowledge_base):
    """Export knowledge base as JSON"""
    output_path = OUTPUT_DIR / "knowledge_base.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(knowledge_base)} knowledge entries to {output_path}")
    return output_path


def export_cleaned_data(df):
    """Export processed patient data as CSV"""
    processed = []

    for idx, row in df.iterrows():
        patient = process_patient(row)
        patient['patient_id'] = idx
        processed.append(patient)

    output_df = pd.DataFrame(processed)
    output_path = OUTPUT_DIR / "cleaned_patients.csv"

    output_df.to_csv(output_path, index=False)
    print(f"Exported {len(processed)} patients to {output_path}")
    return output_path


def main():
    """Export all data"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading and processing data...")
    df, training, knowledge = load_and_process()

    print("\nExporting data files...")
    export_training_data(training)
    export_knowledge_base(knowledge)

    print("\nDone! Files created in data/ directory:")
    print("  - training_data.json")
    print("  - knowledge_base.json")


if __name__ == "__main__":
    main()