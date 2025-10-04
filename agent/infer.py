import os
from pathlib import Path
import joblib
import pandas as pd

MODEL_PATH = os.getenv("MODEL_PATH", "models/clf.joblib")
MODEL_THRESHOLD = float(os.getenv("MODEL_THRESHOLD", "0.55"))
_MODEL = joblib.load(MODEL_PATH) if Path(MODEL_PATH).exists() else None

def score(features: dict) -> float:
    """features needs at least keys: risk, rr"""
    global _MODEL
    if _MODEL is None:
        # try lazy-load once
        if Path(MODEL_PATH).exists():
            _MODEL = joblib.load(MODEL_PATH)
        else:
            return 1.0
    X = pd.DataFrame([{ "risk": float(features.get("risk", 0.0)),
                        "rr":   float(features.get("rr",   0.0)) }])
    proba = _MODEL.predict_proba(X)[0][1] if _MODEL is not None else 1.0
    return float(proba)

def allow(features: dict, threshold: float = None) -> bool:
    t = threshold if threshold is not None else MODEL_THRESHOLD
    return score(features) >= t
