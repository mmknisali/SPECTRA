"""
RAG Query Engine
================
Uses ChromaDB + Ollama (local LLM) to provide treatment recommendations,
patient summaries, and risk assessments.

Flow for each analysis:
    1. Query ChromaDB for similar patients
    2. Build a prompt with similar patient context
    3. Call Ollama LLM with system prompt
    4. Parse JSON response
    5. Fall back to rule-based logic if LLM fails

Fallback protocols are defined inline in this module for the five supported
cancer types.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import chromadb
import pandas as pd
import requests

from backend.config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)
from backend.utils import (
    calculate_risk_score,
    extract_cancer_type,
    extract_labs_from_text,
    flag_abnormal_labs,
)

logger = logging.getLogger("spectra.rag")

# ===========================================================================
# System prompts
# ===========================================================================

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

# ===========================================================================
# ChromaDB helpers
# ===========================================================================


def get_chroma_client() -> Optional[chromadb.PersistentClient]:
    """Get or create a ChromaDB client."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        client.get_collection(name=COLLECTION_NAME)
        return client
    except Exception as e:
        logger.warning("ChromaDB client init failed: %s", e)
        return None


def query_similar_patients(cancer_type: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Query ChromaDB for similar patients by cancer type."""
    client = get_chroma_client()
    if not client:
        return []

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        results = collection.query(
            query_texts=[f"{cancer_type} kanseri tedavi ilaç epikriz"],
            n_results=n_results,
            include=["documents", "metadatas"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        return [
            {
                "document": doc,
                "cancer_type": meta.get("cancer_type", "Bilinmiyor"),
                "gender": meta.get("gender", "Bilinmiyor"),
                "has_epikriz": meta.get("has_epikriz", False),
            }
            for doc, meta in zip(documents, metadatas)
            if doc
        ]
    except Exception as e:
        logger.warning("ChromaDB query failed: %s", e)
        return []


def query_similar_patients_by_text(
    clinical_text: str, n_results: int = 3
) -> List[Dict[str, Any]]:
    """Query ChromaDB for similar patients by clinical text content."""
    client = get_chroma_client()
    if not client:
        return []

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        query = clinical_text[:500] if len(clinical_text) > 500 else clinical_text
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        return [
            {
                "document": doc[:600] if doc else "",
                "cancer_type": meta.get("cancer_type", "Bilinmiyor"),
                "gender": meta.get("gender", "Bilinmiyor"),
                "has_epikriz": meta.get("has_epikriz", False),
            }
            for doc, meta in zip(documents, metadatas)
            if doc
        ]
    except Exception as e:
        logger.warning("ChromaDB query by text failed: %s", e)
        return []

# ===========================================================================
# Ollama helpers
# ===========================================================================


def call_ollama_api(
    prompt: str,
    max_tokens: int = 600,
    system_prompt: Optional[str] = None,
) -> Optional[str]:
    """Call Ollama API with an optional system prompt."""
    sp = system_prompt if system_prompt else TREATMENT_SYSTEM_PROMPT
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{sp}\n\n{prompt}",
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            },
            timeout=OLLAMA_TIMEOUT,
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        logger.warning("Ollama API call failed: %s", e)
    return None


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM JSON response into a structured dict."""
    try:
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "recommended_labs": result.get("recommended_labs", []),
                "treatment_protocol": result.get("treatment_protocol", ""),
                "source": "rag+llm",
            }
    except Exception:
        pass

    return {
        "recommended_labs": [],
        "treatment_protocol": response_text[:500] if response_text else "",
        "source": "rag+llm",
    }

# ===========================================================================
# Prompt building
# ===========================================================================


def build_treatment_prompt(
    cancer_type: str,
    similar_patients: List[Dict[str, Any]],
    patient_labs: Optional[Dict] = None,
) -> str:
    """Build a Turkish prompt for treatment recommendation."""
    prompt = f"Kanser türü: {cancer_type}\n\n"

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
        prompt += f"hastanın laboratuvar sonuçları: {patient_labs}. "

    prompt += """Bu hasta için tedavi önerileri sun.
Lütfen şu bilgileri içeren JSON yanıtı ver:
- recommended_labs: Takip önerilen laboratuvar testleri
- treatment_protocol: Detaylı tedavi protokolü açıklaması (en az 2-3 cümle)"""

    return prompt

# ===========================================================================
# Treatment recommendation
# ===========================================================================


def get_treatment_recommendation(
    cancer_type: str,
    patient_labs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Get treatment recommendation using RAG + LLM with fallback."""
    similar_patients = query_similar_patients(cancer_type, n_results=3)
    prompt = build_treatment_prompt(cancer_type, similar_patients, patient_labs)
    llm_response = call_ollama_api(prompt)

    if llm_response:
        result = parse_llm_response(llm_response)
    else:
        result = get_fallback_recommendation(cancer_type)

    result["cancer_type"] = cancer_type
    return result


def get_fallback_recommendation(cancer_type: str) -> Dict[str, Any]:
    """Rule-based fallback recommendation when no LLM is available."""
    fallback_map = {
        "karaciğer kanseri": {
            "recommended_labs": ["AFP", "AST", "ALT", "Bilirubin", "Albumin", "ALP", "GGT"],
            "treatment_protocol": (
                "Hepatosellüler karsinomda BCLC evreleme sistemine göre tedavi planlanır. "
                "Erken evre hastalarda cerrahi rezeksiyon veya ablasyon düşünülür. "
                "İleri evre hastalarda sistemik tedavi olarak tirozin kinaz inhibitörleri "
                "(Sorafenib, Lenvatinib) veya immünoterapi (Atezolizumab + Bevacizumab) kullanılır."
            ),
        },
        "meme kanseri": {
            "recommended_labs": ["CEA", "CA 15-3", "Tam kan sayımı", "Karaciğer fonksiyon testleri"],
            "treatment_protocol": (
                "Meme kanserinde tedavi evreye göre planlanır. Erken evrede cerrahi "
                "(mastektomi veya koruyucu cerrahi) + radyoterapi önerilir. Adjuvan "
                "kemoterapi (AC, FEC protokolleri) ve hormonoterapi (Tamoksifen, Aromataz "
                "inhibitörleri) uygulanır. İleri evrede kemoterapi ve hedefe yönelik "
                "tedaviler (Trastuzumab, CDK4/6 inhibitörleri) kullanılır."
            ),
        },
        "multipl miyelom": {
            "recommended_labs": [
                "Serum protein elektroforezi", "Serbest kappa/lambda",
                "Kreatinin", "Kalsiyum", "Beta-2 mikroglobulin",
            ],
            "treatment_protocol": (
                "Multipl miyelomda ilk basamak tedavi genellikle bortezomib + lenalidomid "
                "+ deksametazon (VRd) kombinasyonudur. İkinci basamakta daratumumab veya "
                "karfilzomib içeren rejimler kullanılır. Otolog kök hücre nakli uygun "
                "hastalarda düşünülmelidir."
            ),
        },
        "over kanseri": {
            "recommended_labs": ["CA-125", "HE4", "Tam kan sayımı", "Kreatinin", "LFT"],
            "treatment_protocol": (
                "Over kanserinde standart tedavi cerrahi (tümör debulking) + platin bazlı "
                "kemoterapidir. İlk basamakta karboplatin + paklitaksel (CarboTaxol) "
                "kullanılır. BRCA mutasyonlu hastalarda PARP inhibitörleri (olaparib) "
                "önemli rol oynamaktadır."
            ),
        },
        "prostat kanseri": {
            "recommended_labs": ["PSA", "Testosteron", "Tam kan sayımı", "Kreatinin", "ALP"],
            "treatment_protocol": (
                "Prostat kanserinde lokalize hastalıkta radikal prostatektomi veya "
                "radyoterapi önerilir. Metastatik hormon duyarlı hastalıkta androjen "
                "deprivasyon tedavisi (ADT) başlanır. Kastrasyon dirençli hastalıkta "
                "abirateron, enzalutamid veya doketaksel kullanılır."
            ),
        },
    }

    key = cancer_type.lower().strip()
    if key in fallback_map:
        return {**fallback_map[key], "source": "fallback"}

    return {
        "recommended_labs": ["Genel durum değerlendirmesi"],
        "treatment_protocol": (
            f"{cancer_type} tedavisi için multidisipliner onkoloji konseyinde "
            "değerlendirilmesi ve literatüre uygun protokol uygulanması önerilir."
        ),
        "source": "fallback",
    }

# ===========================================================================
# Patient summary
# ===========================================================================


def get_fallback_summary(clinical_text: str, lab_text: str) -> Dict[str, Any]:
    """Rule-based fallback for patient summary when no LLM."""
    cancer = extract_cancer_type(clinical_text)
    labs = extract_labs_from_text(lab_text or clinical_text)
    drug_matches = re.findall(r"\[([^\]]+)\]", clinical_text)
    drugs = list({d.strip() for d in drug_matches})[:8]

    findings: List[str] = []
    text_lower = clinical_text.lower()
    if "metastaz" in text_lower:
        findings.append("Metastatik hastalık")
    if "opere" in text_lower:
        findings.append("Cerrahi geçirmiş")
    if "kemoterapi" in text_lower or "kt" in text_lower:
        findings.append("Kemoterapi almış")
    if "radyoterapi" in text_lower or "rt" in text_lower:
        findings.append("Radyoterapi almış")

    return {
        "cancer_type": cancer or "Belirlenemedi",
        "stage": "Belirtilmemiş",
        "treatment_history": findings if findings else ["Bilgi yok"],
        "current_medications": drugs if drugs else ["Belirtilmemiş"],
        "key_findings": [clinical_text[:200]] if clinical_text else ["Klinik not girilmemiş"],
        "performance_status": "Belirtilmemiş",
        "source": "fallback",
    }


def analyze_patient_summary(
    clinical_text: str, lab_text: str = ""
) -> Dict[str, Any]:
    """Generate structured patient summary from clinical text (RAG + LLM)."""
    if not clinical_text or len(clinical_text.strip()) < 10:
        return get_fallback_summary(clinical_text, lab_text)

    similar = query_similar_patients_by_text(clinical_text, n_results=2)

    prompt_parts = [
        "Aşağıdaki hasta klinik metnini analiz et. Hastanın kanser türünü, "
        "evresini, tedavi geçmişini ve mevcut durumunu çıkar.\n",
        f"Hasta klinik metni:\n{clinical_text[:1500]}\n",
    ]
    if lab_text:
        prompt_parts.append(f"Laboratuvar sonuçları:{lab_text[:800]}\n")
    if similar:
        prompt_parts.append("Benzer hasta örnekleri:\n")
        for i, p in enumerate(similar, 1):
            prompt_parts.append(
                f"\nBenzer hasta {i} ({p['cancer_type']}):\n{p['document'][:400]}\n"
            )
    prompt_parts.append("\nHasta özetini JSON formatında ver.")

    llm_response = call_ollama_api(
        "".join(prompt_parts), max_tokens=800, system_prompt=SUMMARY_SYSTEM_PROMPT,
    )

    if llm_response:
        try:
            json_match = re.search(r"\{[\s\S]*\}", llm_response)
            if json_match:
                result = json.loads(json_match.group())
                result["source"] = "rag+llm"
                return result
        except Exception:
            pass

    return get_fallback_summary(clinical_text, lab_text)

# ===========================================================================
# Risk assessment
# ===========================================================================


def get_fallback_risk(clinical_text: str, lab_text: str) -> Dict[str, Any]:
    """Rule-based fallback for risk assessment when no LLM."""
    labs = extract_labs_from_text(lab_text or clinical_text)
    abnormal = flag_abnormal_labs(labs)
    combined = (clinical_text + " " + (lab_text or "")).lower()

    risk_factors: List[str] = []
    if "metastaz" in combined:
        risk_factors.append("Metastaz varlığı")
    if "nüks" in combined or "rekürrens" in combined:
        risk_factors.append("Nüks/Rekürrens")
    if "kemoterapi" in combined:
        risk_factors.append("Aktif kemoterapi alıyor")
    if "palyatif" in combined:
        risk_factors.append("Palyatif bakım ihtiyacı")
    if "kötü" in combined or "ileri evre" in combined:
        risk_factors.append("İleri evre hastalık")

    metastasis: List[str] = []
    for site in ["karaciğer", "akciğer", "kemik", "beyin", "lenf"]:
        if site in combined:
            metastasis.append(f"{site} metastazı")

    level, _ = calculate_risk_score(risk_factors, abnormal, metastasis)

    return {
        "risk_level": level,
        "risk_factors": risk_factors or ["Belirgin risk faktörü tespit edilmedi"],
        "abnormal_labs": abnormal or ["Anormal lab değeri tespit edilmedi"],
        "metastasis_indicators": metastasis or ["Metastaz bulgusu tespit edilmedi"],
        "recommendations": [
            f"Hasta {'yakın takip' if level != 'düşük' else 'rutin takip'} önerilir.",
            (
                "Multidisipliner onkoloji konseyinde değerlendirilmesi önerilir."
                if level == "yüksek"
                else "Standart protokole göre takip edilebilir."
            ),
        ],
        "source": "fallback",
    }


def analyze_risk_assessment(
    clinical_text: str, lab_text: str = ""
) -> Dict[str, Any]:
    """Generate risk assessment from clinical text (RAG + LLM)."""
    if not clinical_text or len(clinical_text.strip()) < 10:
        return get_fallback_risk(clinical_text, lab_text)

    similar = query_similar_patients_by_text(clinical_text, n_results=2)
    labs = extract_labs_from_text(lab_text or clinical_text)
    abnormal = flag_abnormal_labs(labs)

    prompt_parts = [
        "Aşağıdaki hasta verilerini analiz et ve risk değerlendirmesi yap.\n",
        f"Klinik metin:\n{clinical_text[:1500]}\n",
    ]
    if lab_text:
        prompt_parts.append(f"Laboratuvar sonuçları:{lab_text[:800]}\n")
    if abnormal:
        prompt_parts.append(f"Anormal lab değerleri:{abnormal}\n")
    if similar:
        prompt_parts.append("Benzer hasta örnekleri:\n")
        for i, p in enumerate(similar, 1):
            prompt_parts.append(
                f"\nBenzer hasta {i} ({p['cancer_type']}):\n{p['document'][:400]}\n"
            )
    prompt_parts.append("\nRisk değerlendirmesini JSON formatında ver.")

    llm_response = call_ollama_api(
        "".join(prompt_parts), max_tokens=600, system_prompt=RISK_SYSTEM_PROMPT,
    )

    if llm_response:
        try:
            json_match = re.search(r"\{[\s\S]*\}", llm_response)
            if json_match:
                result = json.loads(json_match.group())
                result["source"] = "rag+llm"
                return result
        except Exception:
            pass

    return get_fallback_risk(clinical_text, lab_text)

# ===========================================================================
# ChromaDB indexing
# ===========================================================================


def index_patient_data(df: pd.DataFrame) -> int:
    """Index patient data from a DataFrame into ChromaDB.

    Args:
        df: DataFrame with patient data.

    Returns:
        Number of documents indexed.
    """
    client = get_chroma_client()
    if not client:
        try:
            CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        except Exception as e:
            logger.error("Cannot create ChromaDB client: %s", e)
            return 0

    try:
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        count = collection.count()
        if count > 0:
            logger.info("ChromaDB already has %d documents, skipping indexing", count)
            return count
    except Exception as e:
        logger.error("ChromaDB collection error: %s", e)
        return 0

    indexed = 0
    batch_size = 100
    batch_docs: List[str] = []
    batch_metas: List[Dict[str, Any]] = []
    batch_ids: List[str] = []

    for row in df.itertuples(index=True):
        idx = row.Index
        epikriz = str(getattr(row, "epikriz", "") or "")
        hikaye = str(getattr(row, "hikaye", "") or "")
        lab = str(getattr(row, "lab_sonuclari", "") or "")
        ilac = str(getattr(row, "ilac", "") or "")
        cinsiyet = str(getattr(row, "cinsiyet", "") or "")
        department = str(getattr(row, "department", "") or "")

        cancer = extract_cancer_type(epikriz + " " + hikaye)
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
                collection.add(
                    documents=batch_docs, metadatas=batch_metas, ids=batch_ids,
                )
                indexed += len(batch_docs)
                logger.info("Indexed %d patients so far...", indexed)
            except Exception as e:
                logger.warning("Batch insert failed: %s", e)
            batch_docs, batch_metas, batch_ids = [], [], []

    # Insert remaining documents
    if batch_docs:
        try:
            collection.add(
                documents=batch_docs, metadatas=batch_metas, ids=batch_ids,
            )
            indexed += len(batch_docs)
        except Exception as e:
            logger.warning("Final batch insert failed: %s", e)

    logger.info("Total indexed: %d patients", indexed)
    return indexed


def check_rag_system() -> Dict[str, Any]:
    """Check RAG system status."""
    client = get_chroma_client()
    if not client:
        return {"ready": False, "document_count": 0, "error": "ChromaDB not available"}

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        count = collection.count()
        return {"ready": True, "document_count": count}
    except Exception as e:
        return {"ready": False, "document_count": 0, "error": str(e)}
