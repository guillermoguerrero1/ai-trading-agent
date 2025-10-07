import json
import os
from pathlib import Path
import pandas as pd
import numpy as np
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

# Environment variables for training configuration
VALIDATION_SPLIT = float(os.getenv("VALIDATION_SPLIT", "0.2"))  # Last N% as validation
RECENT_LIVE_PCT = float(os.getenv("RECENT_LIVE_PCT", "0.3"))   # Last K% for recent live metrics

def time_based_split(df, validation_split=0.2):
    """Split dataset by time: last N% as validation."""
    if len(df) < 2:
        return df, df  # Return same data for both if too small
    
    split_idx = int(len(df) * (1 - validation_split))
    train_df = df.iloc[:split_idx].copy()
    val_df = df.iloc[split_idx:].copy()
    
    return train_df, val_df

def get_recent_live_data(df, recent_pct=0.3):
    """Get recent live data (last K% and is_backfill==false)."""
    if len(df) < 2:
        return df
    
    recent_idx = int(len(df) * (1 - recent_pct))
    recent_df = df.iloc[recent_idx:].copy()
    
    # Filter to only live (non-backfill) data
    live_df = recent_df[~recent_df["is_backfill"]].copy()
    
    return live_df

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
        working_df = df.copy()
        y = (df["label"]==1).astype(int)  # win=1, everything else=0
    else:
        # Use only non-zero labels for binary classification
        working_df = non_zero_df.copy()
        y = (non_zero_df["label"]==1).astype(int)  # win=1, loss=0
    
    # Time-based split (already sorted by timestamp in build_dataset)
    train_df, val_df = time_based_split(working_df, VALIDATION_SPLIT)
    
    # Prepare features and labels
    X_tr = train_df[["risk","rr"]].fillna(0.0)
    y_tr = (train_df["label"]==1).astype(int)
    X_val = val_df[["risk","rr"]].fillna(0.0)
    y_val = (val_df["label"]==1).astype(int)
    
    # Get sample weights if available
    sample_weight_tr = train_df.get("weight", None)
    sample_weight_val = val_df.get("weight", None)
    
    # Handle small datasets
    if len(X_tr) < 2:
        print(f"Very small training set ({len(X_tr)} samples), using all data for training")
        X_tr, y_tr = X_val, y_val
        sample_weight_tr = sample_weight_val

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
        "n_samples": len(working_df),
        "n_train": len(X_tr),
        "n_val": len(X_val),
        "validation_split": VALIDATION_SPLIT,
        "recent_live_pct": RECENT_LIVE_PCT,
        "calibration": "sigmoid" if len(X_tr) >= 6 else "none",
        "features": "risk,rr",
        "use_sample_weights": sample_weight_tr is not None
    })
    
    # Log feature names as a tag (not param)
    mlflow.set_tag("feature_names", "risk,rr")
    
    # Train model with sample weights if available
    if sample_weight_tr is not None:
        model.fit(X_tr, y_tr, clf__sample_weight=sample_weight_tr)
        print(f"Trained with sample weights (backfill weight: {sample_weight_tr.mean():.2f})")
    else:
        model.fit(X_tr, y_tr)

    # Calculate metrics for validation_all
    proba_val = model.predict_proba(X_val)[:,1]
    preds_val = (proba_val >= 0.5).astype(int)
    
    metrics = {
        "validation_all_roc_auc": float(roc_auc_score(y_val, proba_val)) if len(set(y_val))>1 else None,
        "validation_all_accuracy": float(accuracy_score(y_val, preds_val)),
        "validation_all_precision": float(precision_score(y_val, preds_val, zero_division=0)),
        "validation_all_recall": float(recall_score(y_val, preds_val, zero_division=0)),
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "features": ["risk","rr"]
    }
    
    # Calculate metrics for validation_recent_live
    recent_live_df = get_recent_live_data(val_df, RECENT_LIVE_PCT)
    if len(recent_live_df) > 0:
        X_recent = recent_live_df[["risk","rr"]].fillna(0.0)
        y_recent = (recent_live_df["label"]==1).astype(int)
        
        proba_recent = model.predict_proba(X_recent)[:,1]
        preds_recent = (proba_recent >= 0.5).astype(int)
        
        metrics.update({
            "validation_recent_live_roc_auc": float(roc_auc_score(y_recent, proba_recent)) if len(set(y_recent))>1 else None,
            "validation_recent_live_accuracy": float(accuracy_score(y_recent, preds_recent)),
            "validation_recent_live_precision": float(precision_score(y_recent, preds_recent, zero_division=0)),
            "validation_recent_live_recall": float(recall_score(y_recent, preds_recent, zero_division=0)),
            "n_recent_live": int(len(recent_live_df))
        })
        
        print(f"Recent live validation: {len(recent_live_df)} samples")
    else:
        print("No recent live data for validation")
        metrics["n_recent_live"] = 0

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
        working_df = df.copy()
        y = (df["label"]==1).astype(int)  # win=1, everything else=0
    else:
        # Use only non-zero labels for binary classification
        working_df = non_zero_df.copy()
        y = (non_zero_df["label"]==1).astype(int)  # win=1, loss=0
    
    # Time-based split (already sorted by timestamp in build_dataset)
    train_df, val_df = time_based_split(working_df, VALIDATION_SPLIT)
    
    # Prepare features and labels
    X_tr = train_df[["risk","rr"]].fillna(0.0)
    y_tr = (train_df["label"]==1).astype(int)
    X_val = val_df[["risk","rr"]].fillna(0.0)
    y_val = (val_df["label"]==1).astype(int)
    
    # Get sample weights if available
    sample_weight_tr = train_df.get("weight", None)
    sample_weight_val = val_df.get("weight", None)
    
    # Handle small datasets
    if len(X_tr) < 2:
        print(f"Very small training set ({len(X_tr)} samples), using all data for training")
        X_tr, y_tr = X_val, y_val
        sample_weight_tr = sample_weight_val

    base = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    
    # Use calibration only if we have enough data for cross-validation
    if len(X_tr) >= 6:  # Need at least 6 samples for 3-fold CV
        # Probability calibration (isotonic tends to be conservative on small data; sigmoid is safer)
        model = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    else:
        print(f"Very small dataset ({len(X_tr)} samples), using uncalibrated model")
        model = base
    
    # Train model with sample weights if available
    if sample_weight_tr is not None:
        model.fit(X_tr, y_tr, clf__sample_weight=sample_weight_tr)
        print(f"Trained with sample weights (backfill weight: {sample_weight_tr.mean():.2f})")
    else:
        model.fit(X_tr, y_tr)

    # Calculate metrics for validation_all
    proba_val = model.predict_proba(X_val)[:,1]
    preds_val = (proba_val >= 0.5).astype(int)
    
    metrics = {
        "validation_all_roc_auc": float(roc_auc_score(y_val, proba_val)) if len(set(y_val))>1 else None,
        "validation_all_accuracy": float(accuracy_score(y_val, preds_val)),
        "validation_all_precision": float(precision_score(y_val, preds_val, zero_division=0)),
        "validation_all_recall": float(recall_score(y_val, preds_val, zero_division=0)),
        "n_train": int(len(X_tr)),
        "n_val": int(len(X_val)),
        "features": ["risk","rr"]
    }
    
    # Calculate metrics for validation_recent_live
    recent_live_df = get_recent_live_data(val_df, RECENT_LIVE_PCT)
    if len(recent_live_df) > 0:
        X_recent = recent_live_df[["risk","rr"]].fillna(0.0)
        y_recent = (recent_live_df["label"]==1).astype(int)
        
        proba_recent = model.predict_proba(X_recent)[:,1]
        preds_recent = (proba_recent >= 0.5).astype(int)
        
        metrics.update({
            "validation_recent_live_roc_auc": float(roc_auc_score(y_recent, proba_recent)) if len(set(y_recent))>1 else None,
            "validation_recent_live_accuracy": float(accuracy_score(y_recent, preds_recent)),
            "validation_recent_live_precision": float(precision_score(y_recent, preds_recent, zero_division=0)),
            "validation_recent_live_recall": float(recall_score(y_recent, preds_recent, zero_division=0)),
            "n_recent_live": int(len(recent_live_df))
        })
        
        print(f"Recent live validation: {len(recent_live_df)} samples")
    else:
        print("No recent live data for validation")
        metrics["n_recent_live"] = 0

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