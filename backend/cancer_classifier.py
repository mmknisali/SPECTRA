"""
Cancer Type Classifier (XGBoost)
=================================
Trains an XGBoost model on patient lab values to predict cancer type.

Features:
    - 17 raw lab columns (from config.ML_LAB_COLUMNS)
    - 2 engineered features: AST/ALT ratio, Creatinine/BUN ratio

Output:
    models/cancer_classifier.joblib
    models/feature_scaler.joblib
    models/label_encoder.joblib

Usage:
    python -m backend.cancer_classifier
"""

from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from backend.config import ML_LAB_COLUMNS, MODELS_DIR
from backend.data_processor import load_dataset
from backend.utils import clean_string_column, extract_cancer_type


def extract_features(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """Extract feature matrix from patient lab columns.

    Args:
        df: DataFrame with patient data.

    Returns:
        Tuple of (feature_matrix, feature_names).
    """
    X = []
    for _, row in df.iterrows():
        features = []
        for col in ML_LAB_COLUMNS:
            val = row.get(col, np.nan)
            try:
                features.append(float(val) if pd.notna(val) else 0.0)
            except (ValueError, TypeError):
                features.append(0.0)
        X.append(features)

    return np.array(X), ML_LAB_COLUMNS.copy()


def add_engineered_features(X: np.ndarray) -> np.ndarray:
    """Add engineered features: AST/ALT ratio and Creatinine/BUN ratio.

    Args:
        X: Original feature matrix.

    Returns:
        Feature matrix with engineered features appended.
    """
    # Column indices match ML_LAB_COLUMNS order
    AST_IDX = 6    # ast
    ALT_IDX = 4    # alt
    CREAT_IDX = 2  # kreatinin
    BUN_IDX = 3    # bun

    ratios = []
    for row in X:
        ast_alt = row[AST_IDX] / row[ALT_IDX] if row[ALT_IDX] > 0 else 0.0
        creat_bun = row[CREAT_IDX] / row[BUN_IDX] if row[BUN_IDX] > 0 else 0.0
        ratios.append([ast_alt, creat_bun])

    return np.hstack([X.copy(), np.array(ratios)])


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> xgb.XGBClassifier:
    """Train XGBoost classifier with early stopping.

    Args:
        X_train: Training features.
        y_train: Training labels (encoded).

    Returns:
        Trained XGBoost classifier.
    """
    X_train_sub, X_val, y_train_sub, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train,
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="mlogloss",
    )

    model.fit(
        X_train_sub, y_train_sub,
        eval_set=[(X_val, y_val)],
        early_stopping_rounds=10,
        verbose=False,
    )
    return model


def predict(model: xgb.XGBClassifier, X: np.ndarray) -> Tuple[str, float]:
    """Predict cancer type and confidence.

    Args:
        model: Trained model.
        X: Feature matrix (single sample).

    Returns:
        Tuple of (predicted_class, confidence).
    """
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    return model.classes_[pred], float(max(proba))


def main():
    """Train and save model."""
    print("Loading data...")
    df = load_dataset()

    print("Extracting features...")
    X, feature_names = extract_features(df)
    X = add_engineered_features(X)

    print("Encoding labels...")
    if "kanser_turu" in df.columns:
        y = df["kanser_turu"].apply(clean_string_column).values
    else:
        y = df.apply(
            lambda row: extract_cancer_type(
                str(row.get("epikriz", "")) + " " + str(row.get("hikaye", ""))
            ) or "Bilinmiyor",
            axis=1,
        ).values

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    print(f"Classes: {label_encoder.classes_}")

    print("Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded,
    )

    print("Scaling features...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    print("Training model...")
    model = train_model(X_train, y_train)

    print("Evaluating...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {accuracy:.2%}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODELS_DIR / "cancer_classifier.joblib")
    joblib.dump(scaler, MODELS_DIR / "feature_scaler.joblib")
    joblib.dump(label_encoder, MODELS_DIR / "label_encoder.joblib")

    print(f"\nModel saved to {MODELS_DIR}/")


if __name__ == "__main__":
    main()
