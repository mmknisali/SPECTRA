"""
Data preprocessing module for SPECTRA
Loads, cleans, and structures the cancer patient dataset
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Use absolute path to root
import os
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = ROOT_DIR / "datamedx_veriset_26.xlsx"


def load_dataset(path: str = None) -> pd.DataFrame:
    """Load dataset from Excel or CSV"""
    path = path or str(DATA_PATH)
    if path.endswith('.csv'):
        return pd.read_csv(path)
    return pd.read_excel(path)


def clean_string_column(value):
    """Clean string columns by removing brackets and extra whitespace"""
    if pd.isna(value):
        return ""
    value = str(value)
    value = re.sub(r'^\[|\]$', '', value)
    value = re.sub(r"'", '', value)
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def extract_codes(icd10_string: str) -> List[str]:
    """Extract individual ICD-10 codes from the combined string"""
    if not icd10_string:
        return []
    codes = re.findall(r'([A-Z]\d+\.?\d*)', icd10_string)
    return list(set(codes))


def extract_drugs(medication_string: str) -> List[str]:
    """Extract individual drug names from medication string"""
    if not medication_string:
        return []
    drugs = re.findall(r'\[([^\]]+)\]', medication_string)
    drugs = [d.strip() for d in drugs]
    return list(set(drugs))


def extract_lab_values(row: pd.Series) -> Dict[str, float]:
    """Extract numeric lab values from patient row"""
    lab_columns = ['hba1c', 'üre', 'kreatinin', 'bun', 'alt', 'alp', 'ast', 'ggt',
                 'bilirubin', 'potasyum', 'kalsiyum', 'magnezyum', 'klor',
                 'albumin', 'crp', 'ldh', 'sodyum']

    labs = {}
    for col in lab_columns:
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                try:
                    labs[col] = float(val)
                except (ValueError, TypeError):
                    pass
    return labs


def get_primary_cancer_type(icd10_codes: List[str]) -> Optional[str]:
    """Map ICD-10 code to primary cancer type"""
    mapping = {
        'C22': 'Karaciğer kanseri',
        'C22.0': 'Karaciğer kanseri',
        'C22.9': 'Karaciğer kanseri',
        'C50': 'Meme Kanseri',
        'C50.9': 'Meme Kanseri',
        'C56': 'Over kanseri',
        'C56.9': 'Over kanseri',
        'C61': 'Prostat kanseri',
        'C90': 'Multipl miyelom',
    }

    for code in icd10_codes:
        if code in mapping:
            return mapping[code]
    return None


def process_patient(row: pd.Series) -> Dict:
    """Process a single patient row into structured data"""
    cancer_type = row.get('kanser_turu', '')
    icd10_raw = clean_string_column(row.get('icd10', ''))
    medications_raw = clean_string_column(row.get('ilac', ''))
    gender_raw = clean_string_column(row.get('cinsiyet', ''))
    department = clean_string_column(row.get('department', ''))
    epicrisis = clean_string_column(row.get('epikriz', ''))

    icd10_codes = extract_codes(icd10_raw)
    drugs = extract_drugs(medications_raw)
    lab_values = extract_lab_values(row)

    return {
        'cancer_type': cancer_type,
        'icd10_codes': icd10_codes,
        'icd10_raw': icd10_raw,
        'medications': drugs,
        'gender': gender_raw,
        'department': department,
        'epicrisis': epicrisis[:500] if epicrisis else '',
        'lab_values': lab_values,
    }


def create_training_pairs(df: pd.DataFrame) -> List[Dict]:
    """
    Create Q&A training pairs from patient data
    Each patient generates multiple Q&A examples
    """
    training_data = []

    templates = [
        {
            'prompt': "{cancer} hastası için hangi ilaçlar kullanılır?",
            'input_key': 'medications',
            'format': lambda p: ', '.join(p['medications'][:10]) if p['medications'] else 'Belirtilmemiş'
        },
        {
            'prompt': "{cancer} hastasında hangi lab değerleri takip edilmeli?",
            'input_key': 'lab_values',
            'format': lambda p: ', '.join(p['lab_values'].keys())
        },
        {
            'prompt': "{cancer} için ICD-10 kodları nelerdir?",
            'input_key': 'icd10_codes',
            'format': lambda p: ', '.join(p['icd10_codes'][:5]) if p['icd10_codes'] else 'Belirtilmemiş'
        },
        {
            'prompt': "{cancer} hastası hangi tedaviyi alır?",
            'input_key': 'department',
            'format': lambda p: p['department'][:100] if p['department'] else 'Medikal onkoloji'
        },
    ]

    for idx, row in df.iterrows():
        patient = process_patient(row)
        cancer = patient['cancer_type']
        if not cancer:
            continue

        for template in templates:
            prompt = template['prompt'].format(cancer=cancer)
            response = template['format'](patient)

            training_data.append({
                'instruction': prompt,
                'response': response,
                'cancer_type': cancer,
                'patient_id': idx,
            })

    return training_data


def create_icd10_knowledge_base(df: pd.DataFrame) -> List[Dict]:
    """Create knowledge base from ICD-10 codes"""
    knowledge = {}

    for _, row in df.iterrows():
        raw = clean_string_column(row.get('icd10', ''))
        codes = extract_codes(raw)
        cancer = row.get('kanser_turu', '')

        for code in codes:
            if code not in knowledge:
                knowledge[code] = {
                    'code': code,
                    'cancer_types': set(),
                    'description': raw[:200],
                }
            knowledge[code]['cancer_types'].add(cancer)

    return [
        {
            'code': data['code'],
            'cancer_types': list(data['cancer_types']),
            'description': data['description'],
        }
        for data in knowledge.values()
    ]


def load_and_process() -> Tuple[pd.DataFrame, List[Dict], List[Dict]]:
    """Main function to load and process all data"""
    print("Loading dataset...")
    df = load_dataset()

    print(f"Loaded {len(df)} patients")

    print("Creating training pairs...")
    training_pairs = create_training_pairs(df)

    print("Creating ICD-10 knowledge base...")
    knowledge_base = create_icd10_knowledge_base(df)

    return df, training_pairs, knowledge_base


if __name__ == "__main__":
    df, training, knowledge = load_and_process()
    print(f"Training pairs: {len(training)}")
    print(f"ICD-10 codes: {len(knowledge)}")