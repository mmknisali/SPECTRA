"""
RAG Query Engine for SPECTRA
Uses ChromaDB + Ollama (local LLM) to provide treatment recommendations
"""

import os
import json
import re
import logging
import requests
from typing import Optional, Dict, Any, List
import chromadb
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("spectra.rag")

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
CHROMA_PATH = ROOT_DIR / "data" / "chroma"
COLLECTION_NAME = "spectra_knowledge"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:7b-instruct-q5_K_M")

TREATMENT_SYSTEM_PROMPT = """Sen deneyimli bir tıbbi onkolog uzmanısın. Türk hastanelerinde yıllarca çalışmış ve çeşitli kanser türleri için tedavi protokolleri konusunda geniş deneyime sahipsin.

Görevin, hastanın kliniğine ve tedavi geçmişine dayanarak tedavi önerileri sunmaktır.

Yanıtını sadece JSON formatında ver:
{
  "recommended_labs": ["Lab1", "Lab2", ...],
  "treatment_protocol": "Tedavi protokolü açıklaması",
  "source": "rag+llm"
}

Önemli kurallar:
1. Tüm yanıtlar Türkçe olmalı
2. İlaç isimleri mümkünse Türkçe olarak yazılmalı
3. Lab testleri için Türkçe kısaltmalar kullan
4. Tedavi protokolü en az 2-3 cümle olmalı"""

SUMMARY_SYSTEM_PROMPT = """Sen deneyimli bir tıbbi onkolog uzmanısın. Görevin, hasta epikrizinden ve klinik notlarından yapılandırılmış bir hasta özeti çıkarmaktır.

Verilen klinik metni analiz et ve SADECE JSON formatında yanıt ver:
{
  "cancer_type": "Kanser türü (örn: Meme Kanseri)",
  "stage": "Hastalık evresi (biliniyorsa)",
  "treatment_history": ["Tedavi 1", "Tedavi 2", ...],
  "current_medications": ["İlaç 1", "İlaç 2", ...],
  "key_findings": ["Önemli bulgu 1", "Önemli bulgu 2", ...],
  "performance_status": "ECOG skoru veya genel durum"
}

Önemli kurallar:
1. Tüm yanıt Türkçe olmalı
2. Sadece metinde açıkça belirtilen bilgileri kullan
3. Bilinmeyen alanlar için boş string veya boş liste kullan
4. Kanser türü mutlaka belirtilmelidir"""

RISK_SYSTEM_PROMPT = """Sen deneyimli bir tıbbi onkolog uzmanısın. Görevin, hasta klinik verilerine dayanarak risk değerlendirmesi yapmaktır.

Verilen klinik metni ve laboratuvar sonuçlarını analiz et ve SADECE JSON formatında yanıt ver:
{
  "risk_level": "düşük|orta|yüksek",
  "risk_factors": ["Risk faktörü 1", "Risk faktörü 2", ...],
  "abnormal_labs": ["Anormal lab 1 (değer)", ...],
  "metastasis_indicators": ["Metastaz bulgusu 1", ...],
  "recommendations": ["Öneri 1", "Öneri 2", ...]
}

Önemli kurallar:
1. Tüm yanıt Türkçe olmalı
2. Risk faktörleri: metastaz varlığı, ileri evre, kötü ECOG skoru, anormal lab değerleri
3. Anormal lab değerlerini referans aralıklarına göre değerlendir
4. Öneriler kısa ve klinik olarak anlamlı olmalı"""


def get_chroma_client() -> Optional[chromadb.PersistentClient]:
    """Get ChromaDB client"""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.get_collection(name=COLLECTION_NAME)
        return client
    except Exception as e:
        logger.warning(f"ChromaDB client init failed: {e}")
        return None


def query_similar_patients(cancer_type: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Query ChromaDB for similar patient notes by cancer type"""
    client = get_chroma_client()
    if not client:
        return []

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        results = collection.query(
            query_texts=[f"{cancer_type} kanseri tedavi ilaç epikriz"],
            n_results=n_results,
            include=["documents", "metadatas"]
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        similar_patients = []
        for doc, meta in zip(documents, metadatas):
            if doc:
                similar_patients.append({
                    "document": doc,
                    "cancer_type": meta.get("cancer_type", "Bilinmiyor"),
                    "gender": meta.get("gender", "Bilinmiyor"),
                    "has_epikriz": meta.get("has_epikriz", False)
                })
        return similar_patients

    except Exception as e:
        logger.warning(f"ChromaDB query failed: {e}")
        return []


def query_similar_patients_by_text(clinical_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Query ChromaDB for similar patient notes by clinical text content"""
    client = get_chroma_client()
    if not client:
        return []

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        query = clinical_text[:500] if len(clinical_text) > 500 else clinical_text
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas"]
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        similar_patients = []
        for doc, meta in zip(documents, metadatas):
            if doc:
                similar_patients.append({
                    "document": doc[:600] if doc else "",
                    "cancer_type": meta.get("cancer_type", "Bilinmiyor"),
                    "gender": meta.get("gender", "Bilinmiyor"),
                    "has_epikriz": meta.get("has_epikriz", False)
                })
        return similar_patients

    except Exception as e:
        logger.warning(f"ChromaDB query by text failed: {e}")
        return []


def call_ollama_api(prompt: str, max_tokens: int = 600, system_prompt: Optional[str] = None) -> Optional[str]:
    """Call Ollama API with optional system prompt"""
    sp = system_prompt if system_prompt else TREATMENT_SYSTEM_PROMPT
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{sp}\n\n{prompt}",
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3}
            },
            timeout=120
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama API call failed: {e}")
    return None


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM response into structured format"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "recommended_labs": result.get("recommended_labs", []),
                "treatment_protocol": result.get("treatment_protocol", ""),
                "source": "rag+llm"
            }
    except Exception:
        pass

    return {
        "recommended_labs": [],
        "treatment_protocol": response_text[:500] if response_text else "",
        "source": "rag+llm"
    }


def build_prompt(cancer_type: str, similar_patients: List[Dict[str, Any]], patient_labs: Optional[Dict] = None) -> str:
    """Build Turkish prompt for LLM"""
    prompt = f" kanser türü: {cancer_type}\n\n"

    if similar_patients:
        prompt += "Benzer hastaların tedavi geçmişleri:\n\n"
        for i, patient in enumerate(similar_patients, 1):
            doc = patient["document"]
            if len(doc) > 800:
                doc = doc[:800] + "..."
            prompt += f"Hasta {i} ({patient['cancer_type']}):\n{doc}\n\n"
        prompt += "Yukarıdaki benzer hastaların tedavi deneyimlerine dayanarak, "
    else:
        prompt += "Bu kanser türü için standart tedavi yaklaşımlarına göre, "

    if patient_labs:
        prompt += f" hastanın laboratuvar sonuçları: {patient_labs}. "

    prompt += """Bu hasta için tedavi önerileri sun.
Lütfen şu bilgileri içeren JSON yanıtı ver:
- recommended_labs: Takip önerilen laboratuvar testleri
- treatment_protocol: Detaylı tedavi protokolü açıklaması (en az 2-3 cümle)"""

    return prompt


def get_treatment_recommendation(cancer_type: str, patient_labs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get treatment recommendation using RAG + LLM"""
    similar_patients = query_similar_patients(cancer_type, n_results=3)
    prompt = build_prompt(cancer_type, similar_patients, patient_labs)
    llm_response = call_ollama_api(prompt)

    if llm_response:
        result = parse_llm_response(llm_response)
    else:
        result = get_fallback_recommendation(cancer_type)

    result["cancer_type"] = cancer_type
    return result


def get_fallback_recommendation(cancer_type: str) -> Dict[str, Any]:
    """Fallback recommendation when no LLM is available"""
    fallback_map = {
        "karaciğer kanseri": {
            "recommended_labs": ["AFP", "AST", "ALT", "Bilirubin", "Albumin", "ALP", "GGT"],
            "treatment_protocol": "Hepatosellüler karsinomda BCLC evreleme sistemine göre tedavi planlanır. Erken evre hastalarda cerrahi rezeksiyon veya ablasyon düşünülür. İleri evre hastalarda sistemik tedavi olarak tirozin kinaz inhibitörleri (Sorafenib, Lenvatinib) veya immünoterapi (Atezolizumab + Bevacizumab) kullanılır."
        },
        "meme kanseri": {
            "recommended_labs": ["CA-15.3", "CEA", "HER2", "ER", "PR", "Mamografi"],
            "treatment_protocol": "Meme kanseri tedavisinde cerrahi (mastektomi veya lumpektomi), adjuvan kemoterapi, hormonal tedavi ve radyoterapi kombinasyonu kullanılır. Hormon reseptör pozitif hastalarda endocrine tedavi (Tamoksifen veya aromataz inhibitörleri), HER2 pozitif hastalarda Trastuzumab önerilir."
        },
        "multipl miyelom": {
            "recommended_labs": ["Beta-2 mikroglobulin", "Serbest zincir", "M protein", "Kreatinin", "Kalsiyum"],
            "treatment_protocol": "Multipl miyelom tedavisinde proteazom inhibitörü (Bortezomib), immünomodülatör (Lenalidomid) ve kortikosteroid kombinasyonları kullanılır. Genç hastalarda otolog kök hücre transplantasyonu düşünülür. Yeni tanı hastalarda VRd (Bortezomib, Lenalidomid, Deksametazon) protokolü sıklıkla kullanılır."
        },
        "over kanseri": {
            "recommended_labs": ["CA-125", "HE4", "AFP", "CEA", "Görüntüleme"],
            "treatment_protocol": "Over kanserinde primer debulking cerrahisi standart tedavidir. Ardından platinum bazlı kemoterapi (Karboplatin + Paklitaksel) uygulanır. BRCA mutasyonu taşıyan hastalarda PARP inhibitörleri (Olaparib) bakımda önerilir."
        },
        "prostat kanseri": {
            "recommended_labs": ["PSA", "Serbest PSA", "Kreatinin", "Hb"],
            "treatment_protocol": "Prostat kanseri tedavisi evreye göre değişir. Lokalize hastalıkta radikal prostatektomi veya radyoterapi uygulanır. Metastatik hastalıkta androgen deprivasyon tedavisi (ADT) temel tedavidir. Dirençli hastalıkta abirateron, enzalutamid veya docetaksel kullanılır."
        }
    }

    cancer_lower = cancer_type.lower()
    for key in fallback_map:
        if key in cancer_lower or cancer_lower in key:
            result = fallback_map[key].copy()
            result["source"] = "fallback"
            return result

    return {
        "recommended_labs": [],
        "treatment_protocol": f"{cancer_type} için tedavi planı hastanın bireysel durumuna göre belirlenmelidir. Detaylı değerlendirme için multidisipliner onkoloji konseyi önerilir.",
        "source": "fallback"
    }


def check_rag_system() -> Dict[str, Any]:
    """Check if RAG system is ready"""
    try:
        client = get_chroma_client()
        if not client:
            return {"ready": False, "error": "ChromaDB client not available"}

        collection = client.get_collection(name=COLLECTION_NAME)
        count = collection.count()

        return {
            "ready": count > 0,
            "document_count": count,
            "collection_name": COLLECTION_NAME,
            "chroma_path": str(CHROMA_PATH)
        }
    except Exception as e:
        return {"ready": False, "error": str(e)}


def extract_cancer_from_text(text: str) -> Optional[str]:
    """Extract cancer type from clinical text using keyword matching"""
    if not text:
        return None
    text_lower = text.lower()
    keywords = [
        (["meme kanseri", "meme karsinomu", "meme ca", "meme malign", "meme tümörü"], "Meme Kanseri"),
        (["karaciğer kanseri", "karaciğer karsinomu", "hepatosellüler", "hcc", "hepatom"], "Karaciğer kanseri"),
        (["multipl miyelom", "multiple myelom", "plazma hücreli"], "Multipl miyelom"),
        (["over kanseri", "over karsinomu", "over ca", "yumurtalık kanseri"], "Over kanseri"),
        (["prostat kanseri", "prostat karsinomu", "prostat ca"], "Prostat kanseri"),
        (["akciğer kanseri", "akciğer karsinomu", "akciğer ca", "lung cancer", "küçük hücreli"], "Akciğer kanseri"),
        (["kolon kanseri", "kolon karsinomu", "kolorektal", "rektum kanseri", "bağırsak kanseri"], "Kolon kanseri"),
        (["pankreas kanseri", "pankreas karsinomu", "pankreas ca"], "Pankreas kanseri"),
        (["mide kanseri", "mide karsinomu", "gastric", "gastrik"], "Mide kanseri"),
        (["lenfoma", "hodgkin", "non-hodgkin"], "Lenfoma"),
        (["lösemi"], "Lösemi"),
        (["tiroid kanseri", "tiroid karsinomu"], "Tiroid kanseri"),
    ]
    for kws, cancer_name in keywords:
        for kw in kws:
            if kw in text_lower:
                return cancer_name
    return None


def extract_labs_from_text(lab_text: str) -> Dict[str, str]:
    """Extract lab name + value pairs from free text"""
    if not lab_text:
        return {}
    labs = {}
    patterns = [
        (r'ast[:\s]*([\d.]+)', 'AST'),
        (r'alt[:\s]*([\d.]+)', 'ALT'),
        (r'crp[:\s]*([\d.]+)', 'CRP'),
        (r'kreatinin[:\s]*([\d.]+)', 'Kreatinin'),
        (r'üre[:\s]*([\d.]+)', 'Üre'),
        (r'sodyum[:\s]*([\d.]+)', 'Sodyum'),
        (r'potasyum[:\s]*([\d.]+)', 'Potasyum'),
        (r'kalsiyum[:\s]*([\d.]+)', 'Kalsiyum'),
        (r'albumin[:\s]*([\d.]+)', 'Albumin'),
        (r'bilirubin[:\s]*([\d.]+)', 'Bilirubin'),
        (r'ggt[:\s]*([\d.]+)', 'GGT'),
        (r'ldh[:\s]*([\d.]+)', 'LDH'),
        (r'hba1c[:\s]*([\d.]+)', 'HbA1c'),
        (r'hgb[:\s]*([\d.]+)', 'HGB'),
        (r'wbc[:\s]*([\d.]+)', 'WBC'),
        (r'plt[:\s]*([\d.]+)', 'PLT'),
    ]
    text_lower = lab_text.lower()
    for pattern, name in patterns:
        match = re.search(pattern, text_lower)
        if match:
            labs[name] = match.group(1)
    return labs


def flag_abnormal_labs(labs: Dict[str, str]) -> List[str]:
    """Flag abnormal lab values based on reference ranges"""
    ref_ranges = {
        'AST': (0, 40),
        'ALT': (0, 40),
        'CRP': (0, 5),
        'Kreatinin': (0.5, 1.2),
        'Üre': (10, 50),
        'Sodyum': (135, 145),
        'Potasyum': (3.5, 5.5),
        'Kalsiyum': (8.5, 10.5),
        'Albumin': (3.5, 5.0),
        'Bilirubin': (0, 1.2),
        'GGT': (0, 55),
        'LDH': (0, 250),
        'HbA1c': (4, 6),
        'HGB': (12, 18),
        'WBC': (4, 11),
        'PLT': (150, 450),
    }
    flags = []
    for name, val_str in labs.items():
        try:
            val = float(val_str)
            if name in ref_ranges:
                lo, hi = ref_ranges[name]
                if val < lo:
                    flags.append(f"{name}: {val_str} (DÜŞÜK, normal: {lo}-{hi})")
                elif val > hi:
                    flags.append(f"{name}: {val_str} (YÜKSEK, normal: {lo}-{hi})")
        except ValueError:
            pass
    return flags


def get_fallback_summary(clinical_text: str, lab_text: str) -> Dict[str, Any]:
    """Rule-based fallback for patient summary when no LLM"""
    cancer = extract_cancer_from_text(clinical_text)
    labs = extract_labs_from_text(lab_text or clinical_text)
    drug_matches = re.findall(r'\[([^\]]+)\]', clinical_text)
    drugs = list(set(d.strip() for d in drug_matches))[:8]

    findings = []
    if "metastaz" in clinical_text.lower():
        findings.append("Metastatik hastalık")
    if "opere" in clinical_text.lower():
        findings.append("Cerrahi geçirmiş")
    if "kemoterapi" in clinical_text.lower() or "kt" in clinical_text.lower():
        findings.append("Kemoterapi almış")
    if "radyoterapi" in clinical_text.lower() or "rt" in clinical_text.lower():
        findings.append("Radyoterapi almış")

    return {
        "cancer_type": cancer or "Belirlenemedi",
        "stage": "Belirtilmemiş",
        "treatment_history": findings if findings else ["Bilgi yok"],
        "current_medications": drugs if drugs else ["Belirtilmemiş"],
        "key_findings": [clinical_text[:200]] if clinical_text else ["Klinik not girilmemiş"],
        "performance_status": "Belirtilmemiş",
        "source": "fallback"
    }


def get_fallback_risk(clinical_text: str, lab_text: str) -> Dict[str, Any]:
    """Rule-based fallback for risk assessment when no LLM"""
    labs = extract_labs_from_text(lab_text or clinical_text)
    abnormal = flag_abnormal_labs(labs)
    combined = (clinical_text + " " + (lab_text or "")).lower()

    risk_factors = []
    if "metastaz" in combined or "met" in combined.split():
        risk_factors.append("Metastaz varlığı")
    if "nüks" in combined or "rekürrens" in combined:
        risk_factors.append("Nüks/Rekürrens")
    if "kemoterapi" in combined:
        risk_factors.append("Aktif kemoterapi alıyor")
    if "palyatif" in combined:
        risk_factors.append("Palyatif bakım ihtiyacı")
    if "kötü" in combined or "ileri evre" in combined:
        risk_factors.append("İleri evre hastalık")

    metastasis = []
    for site in ["karaciğer", "akciğer", "kemik", "beyin", "lenf"]:
        if site in combined:
            metastasis.append(f"{site} metastazı")

    score = len(risk_factors) + len(abnormal) + len(metastasis)
    if score >= 4:
        level = "yüksek"
    elif score >= 2:
        level = "orta"
    else:
        level = "düşük"

    return {
        "risk_level": level,
        "risk_factors": risk_factors if risk_factors else ["Belirgin risk faktörü tespit edilmedi"],
        "abnormal_labs": abnormal if abnormal else ["Anormal lab değeri tespit edilmedi"],
        "metastasis_indicators": metastasis if metastasis else ["Metastaz bulgusu tespit edilmedi"],
        "recommendations": [
            f"Hasta {'yakın takip' if level != 'düşük' else 'rutin takip'} önerilir.",
            "Multidisipliner onkoloji konseyinde değerlendirilmesi önerilir." if level == "yüksek" else "Standart protokole göre takip edilebilir."
        ],
        "source": "fallback"
    }


def analyze_patient_summary(clinical_text: str, lab_text: str = "") -> Dict[str, Any]:
    """Generate structured patient summary from clinical text using RAG + LLM"""
    if not clinical_text or len(clinical_text.strip()) < 10:
        return get_fallback_summary(clinical_text, lab_text)

    similar = query_similar_patients_by_text(clinical_text, n_results=2)

    prompt = f"""Aşağıdaki hasta klinik metnini analiz et. Hastanın kanser türünü, evresini, tedavi geçmişini ve mevcut durumunu çıkar.

Hasta klinik metni:
{clinical_text[:1500]}

{"Laboratuvar sonuçları:" + lab_text[:800] if lab_text else ""}

{"Benzer hasta örnekleri:" if similar else ""}
"""
    for i, p in enumerate(similar, 1):
        prompt += f"\nBenzer hasta {i} ({p['cancer_type']}):\n{p['document'][:400]}\n"

    prompt += "\nHasta özetini JSON formatında ver."

    llm_response = call_ollama_api(prompt, max_tokens=800, system_prompt=SUMMARY_SYSTEM_PROMPT)

    if llm_response:
        try:
            json_match = re.search(r'\{[\s\S]*\}', llm_response)
            if json_match:
                result = json.loads(json_match.group())
                result["source"] = "rag+llm"
                return result
        except Exception:
            pass

    return get_fallback_summary(clinical_text, lab_text)


def analyze_risk_assessment(clinical_text: str, lab_text: str = "") -> Dict[str, Any]:
    """Generate risk assessment from clinical text using RAG + LLM"""
    if not clinical_text or len(clinical_text.strip()) < 10:
        return get_fallback_risk(clinical_text, lab_text)

    similar = query_similar_patients_by_text(clinical_text, n_results=2)

    prompt = f"""Aşağıdaki hasta klinik metnini ve laboratuvar sonuçlarını analiz ederek risk değerlendirmesi yap.

Hasta klinik metni:
{clinical_text[:1500]}

{"Laboratuvar sonuçları:" + lab_text[:800] if lab_text else ""}

{"Benzer hasta örnekleri:" if similar else ""}
"""
    for i, p in enumerate(similar, 1):
        prompt += f"\nBenzer hasta {i} ({p['cancer_type']}):\n{p['document'][:400]}\n"

    prompt += "\nRisk değerlendirmesini JSON formatında ver."

    llm_response = call_ollama_api(prompt, max_tokens=800, system_prompt=RISK_SYSTEM_PROMPT)

    if llm_response:
        try:
            json_match = re.search(r'\{[\s\S]*\}', llm_response)
            if json_match:
                result = json.loads(json_match.group())
                result["source"] = "rag+llm"
                return result
        except Exception:
            pass

    return get_fallback_risk(clinical_text, lab_text)


def index_patient_data(df) -> int:
    """Index patient data from DataFrame into ChromaDB"""
    client = get_chroma_client()
    if not client:
        try:
            CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        except Exception as e:
            logger.error(f"Cannot create ChromaDB client: {e}")
            return 0

    try:
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        count = collection.count()
        if count > 0:
            logger.info(f"ChromaDB already has {count} documents, skipping indexing")
            return count
    except Exception as e:
        logger.error(f"ChromaDB collection error: {e}")
        return 0

    indexed = 0
    batch_size = 100
    batch_docs, batch_metas, batch_ids = [], [], []

    for idx, row in df.iterrows():
        epikriz = str(row.get("epikriz", "") or "")
        hikaye = str(row.get("hikaye", "") or "")
        lab = str(row.get("lab_sonuclari", "") or "")
        ilac = str(row.get("ilac", "") or "")
        cinsiyet = str(row.get("cinsiyet", "") or "")
        department = str(row.get("department", "") or "")

        cancer = extract_cancer_from_text(epikriz + " " + hikaye)
        if not cancer:
            continue

        doc_text = f"{epikriz[:1500]} {lab[:500]} {ilac[:300]}"
        if len(doc_text.strip()) < 50:
            continue

        batch_docs.append(doc_text)
        batch_metas.append({
            "cancer_type": cancer,
            "gender": cinsiyet.strip("[]").strip() if cinsiyet else "Bilinmiyor",
            "department": department.strip("[]").strip()[:100] if department else "",
            "has_epikriz": bool(epikriz.strip()),
        })
        batch_ids.append(f"patient_{idx}")

        if len(batch_docs) >= batch_size:
            try:
                collection.add(documents=batch_docs, metadatas=batch_metas, ids=batch_ids)
                indexed += len(batch_docs)
                logger.info(f"Indexed {indexed} patients so far...")
            except Exception as e:
                logger.warning(f"Batch insert failed: {e}")
            batch_docs, batch_metas, batch_ids = [], [], []

    if batch_docs:
        try:
            collection.add(documents=batch_docs, metadatas=batch_metas, ids=batch_ids)
            indexed += len(batch_docs)
        except Exception as e:
            logger.warning(f"Final batch insert failed: {e}")

    logger.info(f"ChromaDB indexing complete: {indexed} patients indexed")
    return indexed


if __name__ == "__main__":
    status = check_rag_system()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    print(f"\nUsing Ollama: {OLLAMA_MODEL} at {OLLAMA_HOST}")