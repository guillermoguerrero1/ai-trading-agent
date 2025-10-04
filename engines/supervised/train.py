import json
import os
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score
import joblib
import mlflow
import mlflow.sklearn
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

DATA = "data/processed/trades_dataset.parquet"
OUT = "models/clf.joblib"
METRICS = "models/metrics.json"

def train():
    # Set up MLflow tracking (use local file tracking if server not available)
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    
    # Start MLflow run
    try:
        with mlflow.start_run(run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            logger.info("Starting model training", tracking_uri=tracking_uri)
            return _train_with_mlflow()
    except Exception as e:
        logger.warning("MLflow tracking failed, falling back to local training", error=str(e))
        return _train_without_mlflow()

def _train_with_mlflow():
    """Train model with MLflow tracking."""
    if not Path(DATA).exists():
        logger.error("Dataset not found", path=DATA)
        print("Dataset not found:", DATA); return 1
    df = pd.read_parquet(DATA)
    if df.empty:
        logger.error("No data to train")
        print("No data to train."); return 1
    
    # Check if we have enough data for binary classification
    non_zero_df = df[df["label"]!=0].copy()
    if len(non_zero_df) < 2:
        print("Insufficient data for binary classification, using all data with 3-class labels")
        # Use all data with 3-class labels: -1 (loss), 0 (breakeven), 1 (win)
        X = df[["risk","rr"]].fillna(0.0)
        y = df["label"].astype(int)
        # Convert to binary: win=1, everything else=0
        y = (y == 1).astype(int)
    else:
        # Use only non-zero labels for binary classification
        df = non_zero_df
        X = df[["risk","rr"]].fillna(0.0)
        y = (df["label"]==1).astype(int)  # win=1, loss=0
    
    # Handle small datasets - use all data for training if too few samples
    if len(X) < 4:
        print(f"Small dataset ({len(X)} samples), using all data for training")
        X_tr, y_tr = X, y
        X_val, y_val = X, y  # Use same data for validation when very small
    else:
        X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.25, shuffle=False)

    base = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    
    # Use calibration only if we have enough data for cross-validation
    if len(X_tr) >= 6:  # Need at least 6 samples for 3-fold CV
        # Probability calibration (isotonic tends to be conservative on small data; sigmoid is safer)
        model = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    else:
        print(f"Very small dataset ({len(X_tr)} samples), using uncalibrated model")
        model = base
    
    # Log parameters
    mlflow.log_params({
        "n_samples": len(X),
        "n_train": len(X_tr),
        "n_val": len(X_val),
        "test_size": 0.25 if len(X) >= 4 else 0.0,
        "calibration": "sigmoid" if len(X_tr) >= 6 else "none",
        "features": "risk,rr"
    })
    
    # Log feature names as a tag (not param)
    mlflow.set_tag("feature_names", "risk,rr")
    
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_val)[:,1]
    preds = (proba >= 0.5).astype(int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_val, proba)) if len(set(y_val))>1 else None,
        "accuracy": float(accuracy_score(y_val, preds)),
        "precision": float(precision_score(y_val, preds, zero_division=0)),
        "recall": float(recall_score(y_val, preds, zero_division=0)),
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "features": ["risk","rr"]
    }

    # Log metrics to MLflow
    mlflow_metrics = {k: v for k, v in metrics.items() if v is not None}
    mlflow.log_metrics(mlflow_metrics)
    
    # Log model
    mlflow.sklearn.log_model(
        model, 
        "model",
        registered_model_name="trading_classifier"
    )
    
    # Save model locally
    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT)
    Path(METRICS).write_text(json.dumps(metrics, indent=2))
    
    # Tag as Production if this is the best model
    run_id = mlflow.active_run().info.run_id
    if _is_best_model(mlflow_metrics):
        mlflow.set_tag("stage", "Production")
        logger.info("Model tagged as Production", run_id=run_id)
        print("Model tagged as Production in MLflow")
    else:
        mlflow.set_tag("stage", "Staging")
        logger.info("Model tagged as Staging", run_id=run_id)
    
    print("Saved", OUT, "and", METRICS)
    print(f"MLflow run ID: {run_id}")
    return 0

def _train_without_mlflow():
    """Train model without MLflow tracking (fallback)."""
    if not Path(DATA).exists():
        print("Dataset not found:", DATA); return 1
    df = pd.read_parquet(DATA)
    if df.empty:
        print("No data to train."); return 1
    
    # Check if we have enough data for binary classification
    non_zero_df = df[df["label"]!=0].copy()
    if len(non_zero_df) < 2:
        print("Insufficient data for binary classification, using all data with 3-class labels")
        # Use all data with 3-class labels: -1 (loss), 0 (breakeven), 1 (win)
        X = df[["risk","rr"]].fillna(0.0)
        y = df["label"].astype(int)
        # Convert to binary: win=1, everything else=0
        y = (y == 1).astype(int)
    else:
        # Use only non-zero labels for binary classification
        df = non_zero_df
        X = df[["risk","rr"]].fillna(0.0)
        y = (df["label"]==1).astype(int)  # win=1, loss=0
    
    # Handle small datasets - use all data for training if too few samples
    if len(X) < 4:
        print(f"Small dataset ({len(X)} samples), using all data for training")
        X_tr, y_tr = X, y
        X_val, y_val = X, y  # Use same data for validation when very small
    else:
        X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.25, shuffle=False)

    base = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    
    # Use calibration only if we have enough data for cross-validation
    if len(X_tr) >= 6:  # Need at least 6 samples for 3-fold CV
        # Probability calibration (isotonic tends to be conservative on small data; sigmoid is safer)
        model = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    else:
        print(f"Very small dataset ({len(X_tr)} samples), using uncalibrated model")
        model = base
    
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_val)[:,1]
    preds = (proba >= 0.5).astype(int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_val, proba)) if len(set(y_val))>1 else None,
        "accuracy": float(accuracy_score(y_val, preds)),
        "precision": float(precision_score(y_val, preds, zero_division=0)),
        "recall": float(recall_score(y_val, preds, zero_division=0)),
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "features": ["risk","rr"]
    }

    # Save model locally
    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT)
    Path(METRICS).write_text(json.dumps(metrics, indent=2))
    
    print("Saved", OUT, "and", METRICS)
    print("Note: MLflow tracking not available, using local training only")
    return 0

def _is_best_model(metrics):
    """Check if this is the best model based on metrics."""
    # Simple heuristic: best if accuracy > 0.6 and precision > 0.5
    return (
        metrics.get("accuracy", 0) > 0.6 and 
        metrics.get("precision", 0) > 0.5
    )

if __name__ == "__main__":
    raise SystemExit(train())