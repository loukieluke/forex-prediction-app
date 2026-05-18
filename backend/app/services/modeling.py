from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from app.config import settings

FEATURE_COLUMNS = [
    "rsi",
    "macd",
    "macd_signal",
    "bb_upper",
    "bb_lower",
    "ema_20",
    "sentiment_score",
]


def _ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def train_model(df: pd.DataFrame, artifact_path: str | None = None) -> dict:
    data = df.copy()
    data["target"] = (data["close"].shift(-1) > data["close"]).astype(int)
    data = data.dropna()
    if data.empty:
        raise ValueError("No training data available after cleaning")
    X = data[FEATURE_COLUMNS]
    y = data["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)
    report = classification_report(y_test, model.predict(X_test), output_dict=True)
    artifact = artifact_path or settings.model_path
    _ensure_parent_dir(artifact)
    joblib.dump(model, artifact)
    return {"artifact_path": artifact, "report": report}


def load_model(path: str | None = None):
    model_path = path or settings.model_path
    return joblib.load(model_path)


def predict_signal(features: dict, model=None, hold_threshold: float | None = None) -> dict:
    classifier = model or load_model()
    threshold = hold_threshold if hold_threshold is not None else settings.prediction_hold_threshold
    row = {k: float(features.get(k) or 0.0) for k in FEATURE_COLUMNS}
    frame = pd.DataFrame([row])
    probs = classifier.predict_proba(frame)[0]
    confidence = float(max(probs))
    if confidence < threshold:
        return {"signal": "HOLD", "confidence": round(confidence, 4)}
    signal = "BUY" if probs[1] > probs[0] else "SELL"
    return {"signal": signal, "confidence": round(confidence, 4)}


def versioned_artifact_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"/app/model_artifacts/model_{stamp}.joblib"
