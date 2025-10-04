from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Depends
import json, os
import mlflow
import mlflow.sklearn
import structlog
from app.deps import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.get("/model/status")
def model_status(request: Request):
    mp = os.getenv("MODEL_PATH", "models/clf.joblib")
    mt = os.getenv("MODEL_THRESHOLD", "0.55")
    metrics_path = "models/metrics.json"
    metrics = json.loads(Path(metrics_path).read_text()) if Path(metrics_path).exists() else {}
    return {
        "model_path": mp,
        "exists": Path(mp).exists(),
        "threshold": float(getattr(request.app.state, "model_threshold", float(mt))),
        "metrics": metrics,
        "gate_enabled": bool(getattr(request.app.state, "require_model_gate", False)),
    }

@router.post("/model/reload")
def model_reload(request: Request, current_user: dict = Depends(get_current_user)):
    # lazy strategy: clear cached model in agent.infer so next call re-loads
    from agent import infer
    infer._MODEL = None
    return {"reloaded": True}

@router.put("/model/threshold")
def model_threshold(request: Request, body: dict, current_user: dict = Depends(get_current_user)):
    thr = float(body.get("threshold", 0.55))
    request.app.state.model_threshold = thr
    return {"threshold": thr}

@router.post("/model/promote")
def promote_model(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Promote the latest Production model from MLflow to be the active model.
    
    Returns:
        Model promotion result
    """
    try:
        # Set up MLflow tracking
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(tracking_uri)
        
        # Get the latest Production model
        client = mlflow.tracking.MlflowClient()
        
        # Search for runs with Production tag
        runs = client.search_runs(
            experiment_ids=["0"],  # Default experiment
            filter_string="tags.stage = 'Production'",
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if not runs:
            raise HTTPException(
                status_code=404,
                detail="No Production model found in MLflow"
            )
        
        latest_run = runs[0]
        run_id = latest_run.info.run_id
        
        # Get model URI
        model_uri = f"runs:/{run_id}/model"
        
        # Download and save the model
        model = mlflow.sklearn.load_model(model_uri)
        
        # Save to local path
        model_path = os.getenv("MODEL_PATH", "models/clf.joblib")
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        
        import joblib
        joblib.dump(model, model_path)
        
        # Update app state
        request.app.state.model_path = model_path
        request.app.state.model_version = run_id
        
        # Clear cached model in agent.infer
        try:
            from agent import infer
            infer._MODEL = None
        except ImportError:
            pass  # agent module might not be available
        
        logger.info("Model promoted successfully", 
                   run_id=run_id, 
                   model_path=model_path)
        
        return {
            "success": True,
            "message": "Model promoted successfully",
            "run_id": run_id,
            "model_path": model_path,
            "model_uri": model_uri
        }
        
    except Exception as e:
        logger.error("Model promotion failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Model promotion failed: {str(e)}"
        )
