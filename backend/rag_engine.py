"""
RAG Query Engine for SPECTRA
Uses ChromaDB + Ollama (local LLM) to provide treatment recommendations
"""

import os
import json
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

SYSTEM_PROMPT = """Sen deneyimli bir tıbbi onkolog uzmanısın. Türk hastanelerinde yıllarca çalışmış ve çeşitli kanser türleri için tedavi protokolleri konusunda geniş deneyime sahipsin.

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
    """Query ChromaDB for similar patient notes"""
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


def call_ollama_api(prompt: str, max_tokens: int = 600) -> Optional[str]:
    """Call Ollama API for treatment recommendation"""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
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
        import re
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


if __name__ == "__main__":
    status = check_rag_system()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    print(f"\nUsing Ollama: {OLLAMA_MODEL} at {OLLAMA_HOST}")