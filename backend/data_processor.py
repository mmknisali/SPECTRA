"""
Data preprocessing module for SPECTRA
Loads, cleans, and structures the cancer patient dataset
Supports Excel (.xlsx) and CSV (.csv) formats
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import os
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = ROOT_DIR / "hackathon_veri.csv"

CANCER_KEYWORDS = [
    (["meme kanseri", "meme karsinomu", "meme ca", "meme malign"], "Meme Kanseri"),
    (["karaciğer kanseri", "karaciğer karsinomu", "hepatosellüler", "hcc", "hepatom"], "Karaciğer kanseri"),
    (["multipl miyelom", "multiple myelom", "plazma hücre"], "Multipl miyelom"),
    (["over kanseri", "over karsinomu", "over ca", "yumurtalık kanseri"], "Over kanseri"),
    (["prostat kanseri", "prostat karsinomu", "prostat ca"], "Prostat kanseri"),
    (["akciğer kanseri", "akciğer karsinomu", "akciğer ca", "lung cancer", "küçük hücreli"], "Akciğer kanseri"),
    (["kolon kanseri", "kolon karsinomu", "kolorektal", "rektum kanseri", "bağırsak kanseri"], "Kolon kanseri"),
    (["pankreas kanseri", "pankreas karsinomu", "pankreas ca"], "Pankreas kanseri"),
    (["mide kanseri", "mide karsinomu", "gastric", "gastrik"], "Mide kanseri"),
    (["mesane kanseri", "mesane ca", "bladder"], "Mesane kanseri"),
    (["böbrek kanseri", "böbrek karsinomu", "renal hücre"], "Böbrek kanseri"),
    (["lenfoma", "hodgkin", "non-hodgkin"], "Lenfoma"),
    (["lösemi", "lösemi"], "Lösemi"),
    (["tiroid kanseri", "tiroid karsinomu", "tiroid ca"], "Tiroid kanseri"),
    (["baş boyun kanseri", "baş boyun"], "Baş boyun kanseri"),
    (["endometriyum kanseri", "endometrium", "rahim kanseri", "uterus"], "Endometriyum kanseri"),
    (["serviks kanseri", "serviks", "rahim ağzı"], "Serviks kanseri"),
    (["malign melanom", "melanom", "melanoma"], "Malign melanom"),
]


def extract_cancer_type(text: str) -> Optional[str]:
    if not text:
        return None
    text_lower = text.lower()
    for keywords, cancer_name in CANCER_KEYWORDS:
        for kw in keywords:
            if kw in text_lower:
                return cancer_name
    return None


def load_dataset(path: str = None) -> pd.DataFrame:
    """Load dataset from Excel or CSV"""
    path = path or str(DATA_PATH)
    if path.endswith('.csv'):
        return pd.read_csv(path, low_memory=False)
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

    if not labs and 'lab_sonuclari' in row.index:
        lab_text = clean_string_column(row.get('lab_sonuclari', ''))
        lab_patterns = {
            'ast': r'ast[:\s]*([\d.]+)',
            'alt': r'alt[:\s]*([\d.]+)',
            'crp': r'crp[:\s]*([\d.]+)',
            'kreatinin': r'kreatinin[:\s]*([\d.]+)',
            'üre': r'üre[:\s]*([\d.]+)',
            'sodyum': r'sodyum[:\s]*([\d.]+)',
            'potasyum': r'potasyum[:\s]*([\d.]+)',
            'kalsiyum': r'kalsiyum[:\s]*([\d.]+)',
            'albumin': r'albumin[:\s]*([\d.]+)',
            'bilirubin': r'bilirubin[:\s]*([\d.]+)',
            'ggt': r'ggt[:\s]*([\d.]+)',
            'ldh': r'ldh[:\s]*([\d.]+)',
            'hba1c': r'hba1c[:\s]*([\d.]+)',
        }
        for lab, pattern in lab_patterns.items():
            match = re.search(pattern, lab_text, re.IGNORECASE)
            if match:
                try:
                    labs[lab] = float(match.group(1))
                except ValueError:
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
    if pd.isna(cancer_type) or not cancer_type:
        for field in ['epikriz', 'hikaye', 'patoloji rapor özet', 'not']:
            text = row.get(field, '')
            if pd.notna(text):
                extracted = extract_cancer_type(str(text))
                if extracted:
                    cancer_type = extracted
                    break

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
    """Create Q&A training pairs from patient data"""
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
    if 'icd10' not in df.columns:
        return []

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

    print("Extracting cancer types from clinical text...")
    has_cancer_col = 'kanser_turu' in df.columns
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
    print(f"Training pairs: {len(training)}")
    print(f"ICD-10 codes: {len(knowledge)}")
