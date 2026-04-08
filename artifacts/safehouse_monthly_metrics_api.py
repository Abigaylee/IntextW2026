from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import pandas as pd
import joblib

app = FastAPI(title="Safehouse Monthly Metrics Prediction API")

bundle = joblib.load("../artifacts/safehouse_monthly_metrics_deploy_bundle.joblib")
model = bundle["model_pipeline"]
required_cols = bundle["required_input_columns"]

def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    # Convert month_start to datetime if present
    if "month_start" in df.columns:
        df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
        # Match training conversion style (ordinal)
        df["month_start"] = df["month_start"].map(lambda x: x.toordinal() if pd.notnull(x) else None)
    return df

class PredictionRequest(BaseModel):
    payload: Dict[str, Any]

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/predict")
def predict(req: PredictionRequest):
    incoming = req.payload

    missing = [c for c in required_cols if c not in incoming]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {missing}")

    row = pd.DataFrame([incoming])[required_cols]
    row = _coerce_types(row)

    pred = float(model.predict(row)[0])
    return {
        "model": bundle["model_name"],
        "target": bundle["target"],
        "prediction": pred
    }
