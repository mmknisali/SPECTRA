"""
SPECTRA - Streamlit Frontend
2-Tab Interface for Oncology Assistant
"""

import streamlit as st
import requests
from typing import Optional
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="SPECTRA - Oncology Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

ACCENT = "#87BAFF"
SECONDARY = "#EFEDDA"

st.markdown(f"""
<style>
    :root {{
        --accent: {ACCENT};
        --secondary: {SECONDARY};
    }}
    .stApp {{
        background: linear-gradient(180deg, #0D1117 0%, #161B22 100%);
        color: {SECONDARY};
    }}
    h1, h2, h3 {{
        color: {ACCENT} !important;
        font-weight: 600;
    }}
    p, div, span {{
        color: {SECONDARY} !important;
    }}
    .stMarkdown {{
        color: {SECONDARY};
    }}
    .stButton>button {{
        background: linear-gradient(135deg, {ACCENT} 0%, #6B9CE8 100%);
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        color: white !important;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(135, 186, 255, 0.4);
    }}
    .stTextArea textarea {{
        background: #21262D;
        border: 1px solid #30363D;
        border-radius: 8px;
        color: {SECONDARY} !important;
    }}
    .stTextArea textarea::placeholder {{
        color: #6E7681;
    }}
    .stSelectbox div[data-baseweb="select"] > div {{
        background: #21262D;
        border: 1px solid #30363D;
        color: {SECONDARY} !important;
    }}
    .stExpander {{
        background: #21262D;
        border: 1px solid #30363D;
        border-radius: 8px;
    }}
    .stSuccess {{
        background: rgba(135, 186, 255, 0.15);
        border: 1px solid {ACCENT};
        border-radius: 8px;
    }}
    .stWarning {{
        background: rgba(255, 200, 80, 0.15);
        border: 1px solid #FFC850;
        border-radius: 8px;
    }}
    .stError {{
        background: rgba(255, 100, 100, 0.15);
        border: 1px solid #FF6464;
        border-radius: 8px;
    }}
    div[data-testid="stSidebar"] {{
        background: #161B22;
        border-right: 1px solid #30363D;
    }}
    .stSidebar .stMarkdown {{
        color: {SECONDARY} !important;
    }}
    .sidebar-status {{
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }}
    .connected {{
        background: rgba(135, 186, 255, 0.15);
        border: 1px solid {ACCENT};
    }}
    .disconnected {{
        background: rgba(255, 100, 100, 0.15);
        border: 1px solid #FF6464;
    }}
    .card {{
        background: #21262D;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }}
    .footer {{
        text-align: center;
        color: #6E7681;
        padding: 2rem;
        font-size: 0.85rem;
    }}
    .stNumberInput input {{
        background: #21262D;
        border: 1px solid #30363D;
        color: {SECONDARY} !important;
    }}
    .stCheckbox label {{
        color: {SECONDARY} !important;
    }}
    div[data-testid="stInputLabel"] {{
        color: {SECONDARY} !important;
    }}
    .stTab {{
        color: {SECONDARY} !important;
    }}
    .stTab[aria-selected="true"] {{
        color: {ACCENT} !important;
    }}
</style>
""", unsafe_allow_html=True)


CANCER_TYPES = [
    "Karaciğer kanseri",
    "Meme Kanseri",
    "Multipl miyelom",
    "Over kanseri",
    "Prostat kanseri"
]


def check_api():
    try:
        response = requests.get(f"{API_BASE}/health", timeout=3)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def predict_icd10(note: str, cancer_type: Optional[str] = None) -> Optional[dict]:
    try:
        response = requests.post(
            f"{API_BASE}/predict/icd10",
            json={"clinical_note": note, "cancer_type": cancer_type},
            timeout=15
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def recommend_treatment(cancer_type: str, labs: Optional[dict] = None) -> Optional[dict]:
    try:
        response = requests.post(
            f"{API_BASE}/recommend/treatment",
            json={"cancer_type": cancer_type, "patient_labs": labs},
            timeout=30
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def main():
    st.title("SPECTRA")
    st.markdown("**System for Predictive Evaluation, Clinical Triage & Risk Assessment**")

    api_status = check_api()

    with st.sidebar:
        st.markdown("### Status")
        if api_status:
            st.markdown(f"""<div class="sidebar-status connected">
                <strong>Connected</strong><br>
                <small>ChromaDB: {'Ready' if api_status.get('chroma_ready') else 'Not ready'}</small><br>
                <small>Ollama: {'Available' if api_status.get('ollama_available') else 'Unavailable'}</small>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="sidebar-status disconnected">
                <strong>Not Connected</strong><br>
                <small>Run: python -m backend.api</small>
            </div>""", unsafe_allow_html=True)

    if not api_status:
        st.warning("API not available. Start with: `python -m backend.api`")
        return

    tab1, tab2 = st.tabs(["ICD-10 Coder", "Treatment Recommender"])

    with tab1:
        st.markdown("### ICD-10 Code Generator")
        st.markdown("Generate diagnostic codes from clinical notes")

        col1, col2 = st.columns([1, 2])
        with col1:
            cancer_type = st.selectbox("Cancer Type", CANCER_TYPES)
        with col2:
            clinical_note = st.text_area("Clinical Notes", height=100, placeholder="Patient presents with...")

        if st.button("Generate Codes", use_container_width=True):
            if not clinical_note:
                st.warning("Enter clinical notes")
            else:
                result = predict_icd10(clinical_note, cancer_type)
                if result:
                    codes = result.get('suggested_codes', [])
                    if codes:
                        st.success(f"Found {len(codes)} codes")
                        for code in codes:
                            with st.expander(f"**{code['code']}** - Score: {code.get('score', 0):.2f}"):
                                st.markdown(f"**Description:** {code.get('description', 'N/A')}")
                                st.markdown(f"**Cancer Types:** {', '.join(code.get('cancer_types', []))}")
                    else:
                        st.warning("No codes found")

    with tab2:
        st.markdown("### Treatment Recommender")
        st.markdown("Evidence-based treatment protocols")

        col1, col2 = st.columns([1, 2])
        with col1:
            cancer_type = st.selectbox("Cancer Type", CANCER_TYPES, key="treatment")
            include_labs = st.checkbox("Include lab values")

        labs = None
        if include_labs:
            with col2:
                st.markdown("**Lab Values**")
                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    ast = st.number_input("AST", 0.0, 500.0, 25.0, key="t_ast")
                    crp = st.number_input("CRP", 0.0, 300.0, 5.0, key="t_crp")
                with lc2:
                    alt = st.number_input("ALT", 0.0, 500.0, 25.0, key="t_alt")
                    ldh = st.number_input("LDH", 0.0, 1000.0, 200.0, key="t_ldh")
                with lc3:
                    alp = st.number_input("ALP", 0.0, 500.0, 80.0, key="t_alp")
                    albumin = st.number_input("Albumin", 0.0, 10.0, 4.0, key="t_albumin")
                labs = {"ast": ast, "alt": alt, "alp": alp, "crp": crp, "ldh": ldh, "albumin": albumin}

        if st.button("Get Recommendations", use_container_width=True):
            result = recommend_treatment(cancer_type, labs)
            if result:
                st.markdown("#### Recommended Labs")
                for lab in result.get('recommended_labs', []):
                    st.markdown(f"- {lab}")

                st.markdown("#### Treatment Protocol")
                st.markdown(result.get('treatment_protocol', 'No protocol available'))

                st.caption(f"Source: {result.get('source', 'unknown')}")

    st.markdown("---")
    st.markdown("""<div class="footer">
        SPECTRA - Oncology Assistant<br>
        AI-Powered Clinical Decision Support
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()