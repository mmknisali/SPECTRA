"""
Cancer Type Classifier using XGBoost
Trains on patient lab values to predict cancer type
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import xgboost as xgb

MODEL_DIR = Path(__file__).parent.parent / "models"


def extract_features(df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
    """Extract feature matrix from patient data"""
    lab_columns = [
        'hba1c', 'üre', 'kreatinin', 'bun', 'alt', 'alp', 'ast', 'ggt',
        'bilirubin', 'potasyum', 'kalsiyum', 'magnezyum', 'klor',
        'albumin', 'crp', 'ldh', 'sodyum'
    ]

    feature_names = []
    X = []

    for idx, row in df.iterrows():
        features = []
        for col in lab_columns:
            val = row.get(col, np.nan)
            try:
                features.append(float(val) if pd.notna(val) else 0.0)
            except (ValueError, TypeError):
                features.append(0.0)
        X.append(features)

        if idx == 0:
            feature_names = lab_columns

    return np.array(X), feature_names


def add_engineered_features(X: np.ndarray, feature_names: list = None) -> np.ndarray:
    """Add engineered features"""
    X_new = X.copy()

    ratios = []
    for row in X:
        ratio = []
        # AST/ALT ratio (De Ritis ratio): AST=index 6, ALT=index 4
        if row[6] > 0:
            ratio.append(row[6] / row[4])
        else:
            ratio.append(0)
        # Creatinine/BUN ratio: Creatinine=index 2, BUN=index 3
        if row[3] > 0:
            ratio.append(row[2] / row[3])
        else:
            ratio.append(0)
        ratios.append(ratio)

    ratios = np.array(ratios)
    return np.hstack([X_new, ratios])


def train_model(X_train: np.ndarray, y_train: np.ndarray, labels: List[str]) -> xgb.XGBClassifier:
    """Train XGBoost classifier"""
    # Split training data to create validation set for early stopping
    X_train_sub, X_val, y_train_sub, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='mlogloss',
        early_stopping_rounds=10,
    )

    model.fit(X_train_sub, y_train_sub, eval_set=[(X_val, y_val)])
    return model


def predict(model: xgb.XGBClassifier, X: np.ndarray) -> Tuple[str, float]:
    """Predict cancer type and confidence"""
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]
    return model.classes_[pred], max(proba)


def main():
    """Train and save model"""
    from .data_processor import load_dataset, clean_string_column

    print("Loading data...")
    df = load_dataset()

    print("Extracting features...")
    X, feature_names = extract_features(df)
    X = add_engineered_features(X)

    print("Encoding labels...")
    y = df['kanser_turu'].apply(clean_string_column).values
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    print(f"Classes: {label_encoder.classes_}")

    print("Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    print("Scaling features...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    print("Training model...")
    model = train_model(X_train, y_train, label_encoder.classes_)

    print("Evaluating...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test accuracy: {accuracy:.2%}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    MODEL_DIR.mkdir(exist_ok=True)

    joblib.dump(model, MODEL_DIR / "cancer_classifier.joblib")
    joblib.dump(scaler, MODEL_DIR / "feature_scaler.joblib")
    joblib.dump(label_encoder, MODEL_DIR / "label_encoder.joblib")

    print(f"\nModel saved to {MODEL_DIR}/")


if __name__ == "__main__":
    main()