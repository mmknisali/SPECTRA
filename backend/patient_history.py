"""
Patient History Module for SPECTRA
==================================
Provides patient timeline, visit history, and clinical decision support
based on longitudinal data from the hospital dataset.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd


@dataclass
class PatientVisit:
    """Represents a single patient visit/encounter."""
    date: Optional[str]
    department: Optional[str]
    visit_type: Optional[str]  # yatış tipi
    admission_type: Optional[str]  # başvuru tipi
    procedure_name: Optional[str]  # işlem adı
    procedure_type: Optional[str]  # işlem tipi
    clinical_notes: Optional[str]  # epikriz
    findings: Optional[str]  # bulgu
    history: Optional[str]  # hikaye
    medications: Optional[List[str]]
    lab_results: Optional[Dict[str, Any]]
    pathology_summary: Optional[str]  # patoloji rapor özet
    genetic_test: Optional[str]
    death_status: Optional[bool]
    death_date: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PatientHistory:
    """Complete patient history with timeline."""
    patient_id: str
    gender: Optional[str]
    birth_date: Optional[str]
    age: Optional[int]
    visits: List[PatientVisit]
    cancer_type: Optional[str]
    stage: Optional[str]
    current_status: str
    
    def get_timeline(self) -> List[Dict[str, Any]]:
        """Return chronological timeline of events."""
        timeline = []
        for visit in sorted(self.visits, key=lambda x: x.date or ""):
            timeline.append({
                "date": visit.date,
                "type": "visit",
                "department": visit.department,
                "procedure": visit.procedure_name,
                "notes": visit.clinical_notes[:200] + "..." if visit.clinical_notes and len(visit.clinical_notes) > 200 else visit.clinical_notes,
                "medications": visit.medications
            })
        return timeline
    
    def get_treatment_summary(self) -> Dict[str, Any]:
        """Summarize treatments received."""
        treatments = {
            "chemotherapy": [],
            "radiotherapy": [],
            "surgery": [],
            "medications": set(),
            "procedures": []
        }
        
        for visit in self.visits:
            if visit.procedure_name:
                proc = visit.procedure_name.lower()
                if any(word in proc for word in ["kemoterapi", "chemo", "sistoplast", "karboplatin", "paklitaks"]):
                    treatments["chemotherapy"].append({
                        "date": visit.date,
                        "name": visit.procedure_name
                    })
                if any(word in proc for word in ["radyoterapi", "radiotherapy", "rt"]):
                    treatments["radiotherapy"].append({
                        "date": visit.date,
                        "name": visit.procedure_name
                    })
                if any(word in proc for word in ["opere", "cerrahi", "surgery"]):
                    treatments["surgery"].append({
                        "date": visit.date,
                        "name": visit.procedure_name
                    })
                treatments["procedures"].append(visit.procedure_name)
            
            if visit.medications:
                treatments["medications"].update(visit.medications)
        
        treatments["medications"] = list(treatments["medications"])
        return treatments


class PatientHistoryManager:
    """Manages patient history data and queries."""
    
    def __init__(self, csv_path: str = "hackathon_veri.csv"):
        self.csv_path = Path(csv_path)
        self.df: Optional[pd.DataFrame] = None
        self.patient_index: Dict[str, List[int]] = {}  # patient_id -> row indices
        self._load_data()
    
    def _load_data(self):
        """Load and index the CSV data."""
        if not self.csv_path.exists():
            print(f"Warning: {self.csv_path} not found. Patient history unavailable.")
            return
        
        try:
            self.df = pd.read_csv(self.csv_path, low_memory=False)
            # Build index
            for idx, row in self.df.iterrows():
                patient_id = str(row.get('client_id', '')).strip()
                if patient_id and patient_id != 'nan':
                    if patient_id not in self.patient_index:
                        self.patient_index[patient_id] = []
                    self.patient_index[patient_id].append(idx)
            print(f"Loaded {len(self.df)} records for {len(self.patient_index)} patients")
        except Exception as e:
            print(f"Error loading patient data: {e}")
    
    def search_patients(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search patients by ID or partial match."""
        if not self.df is not None:
            return []
        
        query = query.lower()
        results = []
        
        for patient_id in self.patient_index:
            if query in patient_id.lower():
                # Get first row for this patient to extract demographics
                idx = self.patient_index[patient_id][0]
                row = self.df.iloc[idx]
                
                results.append({
                    "patient_id": patient_id,
                    "gender": self._extract_gender(row.get('cinsiyet')),
                    "birth_date": self._clean_value(row.get('doğum tarihi')),
                    "department": self._extract_first_department(row.get('department')),
                    "record_count": len(self.patient_index[patient_id])
                })
                
                if len(results) >= limit:
                    break
        
        return results
    
    def get_patient_history(self, patient_id: str) -> Optional[PatientHistory]:
        """Get complete history for a patient."""
        if not self.df is not None or patient_id not in self.patient_index:
            return None
        
        indices = self.patient_index[patient_id]
        visits = []
        
        # Get demographic info from first record
        first_row = self.df.iloc[indices[0]]
        gender = self._extract_gender(first_row.get('cinsiyet'))
        birth_date = self._clean_value(first_row.get('doğum tarihi'))
        age = self._calculate_age(birth_date)
        
        # Extract cancer type from clinical notes
        cancer_type = self._extract_cancer_type(first_row)
        stage = self._extract_stage(first_row)
        
        # Process each visit/record
        for idx in indices:
            row = self.df.iloc[idx]
            visit = self._parse_visit(row)
            visits.append(visit)
        
        # Determine current status
        current_status = self._determine_status(visits)
        
        return PatientHistory(
            patient_id=patient_id,
            gender=gender,
            birth_date=birth_date,
            age=age,
            visits=visits,
            cancer_type=cancer_type,
            stage=stage,
            current_status=current_status
        )
    
    def _parse_visit(self, row: pd.Series) -> PatientVisit:
        """Parse a single row into a PatientVisit."""
        # Parse medications
        medications = self._parse_medications(row.get('ilac'))
        
        # Parse lab results
        labs = self._parse_labs(row.get('lab_sonuclari'))
        
        # Parse dates
        visit_date = self._clean_date(row.get('işlem tarihi') or row.get('oluşturma tarihi'))
        
        return PatientVisit(
            date=visit_date,
            department=self._extract_first_department(row.get('department')),
            visit_type=self._clean_value(row.get('yatış tipi')),
            admission_type=self._clean_value(row.get('başvuru tipi')),
            procedure_name=self._clean_value(row.get('işlem adı')),
            procedure_type=self._clean_value(row.get('işlem tipi')),
            clinical_notes=self._clean_clinical_text(row.get('epikriz')),
            findings=self._clean_value(row.get('bulgu')),
            history=self._clean_value(row.get('hikaye')),
            medications=medications,
            lab_results=labs,
            pathology_summary=self._clean_value(row.get('patoloji rapor özet')),
            genetic_test=self._clean_value(row.get('genetic test')),
            death_status=self._parse_death_status(row.get('ölüm durumu')),
            death_date=self._clean_date(row.get('ölüm tarihi'))
        )
    
    def get_clinical_recommendations(self, patient_id: str) -> Dict[str, Any]:
        """Generate clinical recommendations based on patient history."""
        history = self.get_patient_history(patient_id)
        if not history:
            return {"error": "Patient not found"}
        
        treatments = history.get_treatment_summary()
        timeline = history.get_timeline()
        
        recommendations = {
            "patient_summary": {
                "id": history.patient_id,
                "age": history.age,
                "gender": history.gender,
                "cancer_type": history.cancer_type,
                "stage": history.stage,
                "status": history.current_status
            },
            "treatment_history": treatments,
            "timeline_preview": timeline[:5],  # Last 5 events
            "recommendations": []
        }
        
        # Generate contextual recommendations
        if history.cancer_type:
            cancer_lower = history.cancer_type.lower()
            
            if "meme" in cancer_lower or "breast" in cancer_lower:
                recommendations["recommendations"].append({
                    "priority": "high",
                    "category": "screening",
                    "text": "Meme kanseri takibi: Yıllık mammografi ve meme USG önerilir"
                })
            
            if "karaciğer" in cancer_lower or "liver" in cancer_lower:
                recommendations["recommendations"].append({
                    "priority": "high",
                    "category": "monitoring",
                    "text": "Karaciğer fonksiyon testleri (AST, ALT, AFP) 3 ayda bir takip edilmeli"
                })
            
            if "metastaz" in str(history.visits[-1].clinical_notes).lower():
                recommendations["recommendations"].append({
                    "priority": "critical",
                    "category": "treatment",
                    "text": "Metastatik hastalık: Sistemik tedavi ve ağrı kontrolü değerlendirilmeli"
                })
        
        # Check for missing recent visits
        if timeline:
            last_visit = timeline[-1]
            if last_visit.get('date'):
                try:
                    last_date = datetime.strptime(str(last_visit['date'])[:10], "%Y-%m-%d")
                    days_since = (datetime.now() - last_date).days
                    if days_since > 90:
                        recommendations["recommendations"].append({
                            "priority": "medium",
                            "category": "follow_up",
                            "text": f"Son ziyaret üzerinden {days_since} gün geçti. Kontrol randevusu planlanmalı."
                        })
                except:
                    pass
        
        return recommendations
    
    # Helper methods
    def _clean_value(self, value: Any) -> Optional[str]:
        """Clean and format a value."""
        if pd.isna(value) or value is None:
            return None
        value = str(value).strip()
        # Remove array brackets
        value = re.sub(r'^[\[\(]|[\]\)]$', '', value)
        return value if value else None
    
    def _clean_date(self, value: Any) -> Optional[str]:
        """Extract and format date."""
        value = self._clean_value(value)
        if not value:
            return None
        # Try to parse various date formats
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]:
            try:
                dt = datetime.strptime(value[:10], fmt)
                return dt.strftime("%Y-%m-%d")
            except:
                continue
        return value
    
    def _extract_gender(self, value: Any) -> Optional[str]:
        """Extract gender from value."""
        value = str(value).lower()
        if "kadın" in value or "kadin" in value or "female" in value:
            return "Kadın"
        elif "erkek" in value or "male" in value:
            return "Erkek"
        return None
    
    def _extract_first_department(self, value: Any) -> Optional[str]:
        """Extract first department from array."""
        value = self._clean_value(value)
        if not value:
            return None
        # Split by comma and take first
        parts = value.split(',')
        if parts:
            return parts[0].strip().strip('[]"')
        return value
    
    def _calculate_age(self, birth_date: Optional[str]) -> Optional[int]:
        """Calculate age from birth date."""
        if not birth_date:
            return None
        try:
            bd = datetime.strptime(birth_date[:10], "%Y-%m-%d")
            return int((datetime.now() - bd).days / 365.25)
        except:
            return None
    
    def _parse_medications(self, value: Any) -> List[str]:
        """Parse medication list."""
        value = self._clean_value(value)
        if not value:
            return []
        # Split by common delimiters
        meds = re.split(r'[,;]+', value)
        return [m.strip() for m in meds if m.strip()]
    
    def _parse_labs(self, value: Any) -> Dict[str, Any]:
        """Parse lab results text."""
        value = self._clean_value(value)
        if not value:
            return {}
        
        labs = {}
        # Extract common lab values
        patterns = [
            (r'HGB[:\s]+(\d+\.?\d*)', 'Hemoglobin'),
            (r'WBC[:\s]+(\d+\.?\d*)', 'WBC'),
            (r'PLT[:\s]+(\d+\.?\d*)', 'Platelet'),
            (r'Kreatinin[:\s]+(\d+\.?\d*)', 'Kreatinin'),
            (r'AST[:\s]+(\d+\.?\d*)', 'AST'),
            (r'ALT[:\s]+(\d+\.?\d*)', 'ALT'),
        ]
        
        for pattern, name in patterns:
            match = re.search(pattern, str(value), re.IGNORECASE)
            if match:
                try:
                    labs[name] = float(match.group(1))
                except:
                    pass
        
        return labs
    
    def _parse_death_status(self, value: Any) -> Optional[bool]:
        """Parse death status."""
        if pd.isna(value):
            return None
        value = str(value).lower()
        return "ölüm" in value or "death" in value or value == "1" or value == "true"
    
    def _clean_clinical_text(self, value: Any) -> Optional[str]:
        """Clean clinical text (epikriz)."""
        value = self._clean_value(value)
        if not value:
            return None
        # Remove _x000D_ characters
        value = value.replace('_x000D_', ' ')
        # Normalize whitespace
        value = ' '.join(value.split())
        return value
    
    def _extract_cancer_type(self, row: pd.Series) -> Optional[str]:
        """Extract cancer type from clinical notes."""
        text = str(row.get('epikriz', '')) + ' ' + str(row.get('hikaye', ''))
        text = text.lower()
        
        cancer_types = [
            (r'meme kanseri|meme ca|breast cancer', 'Meme Kanseri'),
            (r'akciğer kanseri|akciger ca|lung cancer', 'Akciğer Kanseri'),
            (r'karaciğer kanseri|karaciger ca|liver cancer|hepatocellular', 'Karaciğer Kanseri'),
            (r'kolon kanseri|kolon ca|colorectal|colon cancer', 'Kolon Kanseri'),
            (r'mide kanseri|gastric ca|stomach cancer', 'Mide Kanseri'),
            (r'pankreas kanseri|pancreatic ca', 'Pankreas Kanseri'),
            (r'over kanseri|ovarian ca|ovary cancer', 'Over Kanseri'),
            (r'prostat kanseri|prostate ca', 'Prostat Kanseri'),
            (r'tiroid kanseri|thyroid ca', 'Tiroid Kanseri'),
        ]
        
        for pattern, name in cancer_types:
            if re.search(pattern, text):
                return name
        
        return None
    
    def _extract_stage(self, row: pd.Series) -> Optional[str]:
        """Extract cancer stage from notes."""
        text = str(row.get('epikriz', '')).lower()
        
        stage_patterns = [
            (r'stage iv|evre 4|metastaz', 'Evre IV (Metastatik)'),
            (r'stage iii|evre 3', 'Evre III'),
            (r'stage ii|evre 2', 'Evre II'),
            (r'stage i|evre 1', 'Evre I'),
        ]
        
        for pattern, name in stage_patterns:
            if re.search(pattern, text):
                return name
        
        return None
    
    def _determine_status(self, visits: List[PatientVisit]) -> str:
        """Determine current patient status."""
        if not visits:
            return "Bilinmiyor"
        
        # Check for death
        for visit in visits:
            if visit.death_status:
                return "Exitus"
        
        # Check last visit date
        last_visit = max(visits, key=lambda x: x.date or "")
        if last_visit.date:
            try:
                last_date = datetime.strptime(str(last_visit.date)[:10], "%Y-%m-%d")
                days_since = (datetime.now() - last_date).days
                if days_since < 30:
                    return "Aktif Tedavi"
                elif days_since < 90:
                    return "Takipte"
                else:
                    return "Kontrol Gerekli"
            except:
                pass
        
        return "Bilinmiyor"


# Singleton instance
_history_manager: Optional[PatientHistoryManager] = None

def get_history_manager() -> PatientHistoryManager:
    """Get or create the patient history manager singleton."""
    global _history_manager
    if _history_manager is None:
        _history_manager = PatientHistoryManager()
    return _history_manager
