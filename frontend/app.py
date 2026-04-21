"""
SPECTRA - Streamlit Frontend
3-Tab Interface for Oncology Assistant
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from typing import Optional

# Configuration
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="SPECTRA - Oncology Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)


def check_api():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        return response.json()
    except:
        return None


def predict_cancer(labs: dict) -> Optional[dict]:
    """Call cancer prediction endpoint"""
    try:
        response = requests.post(f"{API_BASE}/predict/cancer", json=labs, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def predict_icd10(note: str, cancer_type: Optional[str] = None) -> Optional[dict]:
    """Call ICD-10 prediction endpoint"""
    try:
        response = requests.post(
            f"{API_BASE}/predict/icd10",
            json={"clinical_note": note, "cancer_type": cancer_type},
            timeout=10
        )
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def recommend_treatment(cancer_type: str, labs: Optional[dict] = None) -> Optional[dict]:
    """Call treatment recommendation endpoint"""
    try:
        response = requests.post(
            f"{API_BASE}/recommend/treatment",
            json={"cancer_type": cancer_type, "patient_labs": labs},
            timeout=10
        )
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def main():
    st.title("🏥 SPECTRA")
    st.markdown("### System for Predictive Evaluation, Clinical Triage & Risk Assessment")

    api_status = check_api()
    if api_status:
        st.sidebar.success(f"✅ API Connected")
        st.sidebar.json(api_status)
    else:
        st.sidebar.error("❌ API Not Connected")
        st.sidebar.info("Start the API with: `python -m backend.api`")
        return

    tab1, tab2, tab3 = st.tabs([
        "🔬 Cancer Prediction",
        "📋 ICD-10 Coder",
        "💊 Treatment Recommender"
    ])

    with tab1:
        st.header("Cancer Type Prediction")
        st.markdown("Enter lab values to predict cancer type")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Liver Function")
            hba1c = st.number_input("HbA1c (%)", min_value=0.0, max_value=15.0, value=5.5, step=0.1)
            ast = st.number_input("AST (U/L)", min_value=0.0, value=25.0, step=1.0)
            alt = st.number_input("ALT (U/L)", min_value=0.0, value=25.0, step=1.0)
            alp = st.number_input("ALP (U/L)", min_value=0.0, value=80.0, step=1.0)
            ggt = st.number_input("GGT (U/L)", min_value=0.0, value=30.0, step=1.0)
            bilirubin = st.number_input("Bilirubin (mg/dL)", min_value=0.0, value=1.0, step=0.1)

        with col2:
            st.subheader("Kidney Function")
            üre = st.number_input("Üre (mg/dL)", min_value=0.0, value=20.0, step=0.5)
            kreatinin = st.number_input("Kreatinin (mg/dL)", min_value=0.0, value=1.0, step=0.1)
            bun = st.number_input("BUN (mg/dL)", min_value=0.0, value=15.0, step=0.5)

            st.subheader("Other")
            crp = st.number_input("CRP (mg/L)", min_value=0.0, value=5.0, step=0.5)
            ldh = st.number_input("LDH (U/L)", min_value=0.0, value=200.0, step=5.0)
            albumin = st.number_input("Albumin (g/dL)", min_value=0.0, value=4.0, step=0.1)

        if st.button("Predict Cancer Type", type="primary"):
            labs = {
                "hba1c": hba1c,
                "ast": ast,
                "alt": alt,
                "alp": alp,
                "ggt": ggt,
                "bilirubin": bilirubin,
                "üre": üre,
                "kreatinin": kreatinin,
                "bun": bun,
                "crp": crp,
                "ldh": ldh,
                "albumin": albumin,
            }

            result = predict_cancer(labs)

            if result:
                st.success(f"**Predicted Cancer Type: {result['cancer_type']}**")
                st.metric("Confidence", f"{result['confidence']:.1%}")

                preds = result.get('all_predictions', {})
                df = pd.DataFrame(list(preds.items()), columns=['Cancer Type', 'Probability'])
                fig = px.bar(
                    df, x='Cancer Type', y='Probability',
                    color='Probability',
                    color_continuous_scale='Blues',
                    title="All Predictions"
                )
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("ICD-10 Code Generator")
        st.markdown("Generate ICD-10 codes from clinical notes")

        cancer_type = st.selectbox(
            "Cancer Type",
            ["Karaciğer kanseri", "Meme Kanseri", "Multipl miyelom", "Over kanseri", "Prostat kanseri"]
        )

        clinical_note = st.text_area(
            "Clinical Notes",
            height=150,
            placeholder="Enter clinical notes here... e.g., Patient presents with liver mass, elevated AST/ALT..."
        )

        if st.button("Generate ICD-10 Codes", type="primary"):
            if clinical_note or cancer_type:
                result = predict_icd10(clinical_note, cancer_type)

                if result:
                    codes = result.get('suggested_codes', [])
                    if codes:
                        st.success(f"Found {len(codes)} suggested codes")

                        for code in codes:
                            with st.expander(f"{code['code']} - {code.get('score', 0):.2f}"):
                                st.markdown(f"**Description:** {code.get('description', 'N/A')}")
                                st.markdown(f"**Cancer Types:** {', '.join(code.get('cancer_types', []))}")
                    else:
                        st.warning("No codes found")
            else:
                st.warning("Please enter clinical notes or select cancer type")

    with tab3:
        st.header("Treatment Recommender")
        st.markdown("Get treatment recommendations for cancer type")

        cancer_type = st.selectbox(
            "Cancer Type",
            ["Karaciğer kanseri", "Meme Kanseri", "Multipl miyelom", "Over kanseri", "Prostat kanseri"],
            key="treatment"
        )

        custom_labs = st.checkbox("Include lab values")

        labs = None
        if custom_labs:
            st.markdown("### Lab Values (optional)")
            col1, col2 = st.columns(2)
            with col1:
                ast = st.number_input("AST", min_value=0.0, value=25.0, key="t_ast")
                alt = st.number_input("ALT", min_value=0.0, value=25.0, key="t_alt")
            with col2:
                crp = st.number_input("CRP", min_value=0.0, value=5.0, key="t_crp")

            labs = {"ast": ast, "alt": alt, "crp": crp}

        if st.button("Get Recommendations", type="primary"):
            result = recommend_treatment(cancer_type, labs)

            if result:
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("💊 Recommended Medications")
                    for med in result.get('recommended_medications', []):
                        st.markdown(f"- {med}")

                    st.subheader("🔬 Recommended Labs")
                    for lab in result.get('recommended_labs', []):
                        st.markdown(f"- {lab}")

                with col2:
                    st.subheader("📋 Treatment Protocols")
                    for proto in result.get('protocols', []):
                        st.markdown(f"- {proto}")

    st.markdown("---")
    st.markdown(
        "*SPECTRA - Oncology Assistant | *Made with ❤️ for healthcare*",
        help=None,
        unsafe_allow_html=False
    )


if __name__ == "__main__":
    main()