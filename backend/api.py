import os
import sys
import time
import joblib
import numpy as np
from collections import deque
from typing import Dict, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from forecast import load_forecast_models, predict_future

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "congestion_model.joblib")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found at {MODEL_PATH}. "
        "Run 'python backend/train_model.py' first!"
    )

model = joblib.load(MODEL_PATH)
RISK_LABELS = ["Low", "Medium", "High"]
prediction_history = deque(maxlen=100)
snapshot_store = deque(maxlen=50)
latest_prediction = None

xgb_density_model, xgb_risk_model = load_forecast_models()
xgb_available = xgb_density_model is not None
print(f"  XGBoost forecast: {'LOADED' if xgb_available else 'NOT TRAINED (run: python backend/forecast.py)'}")

app = FastAPI(
    title="Urban Pulse AI",
    description="Crowd congestion prediction API with zone analytics and XGBoost forecasting",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CrowdData(BaseModel):
    density: float
    speed: float
    trend: float = 0.0
    acceleration: float = 0.0
    zones: Dict[str, int] = {}
    flow_direction: str = "Stationary"


class PredictionResponse(BaseModel):
    density: float
    speed: float
    trend: float
    acceleration: float
    zones: Dict[str, int]
    hottest_zone: str
    flow_direction: str
    risk_level: str
    confidence: float
    reason: str


def get_hottest_zone(zones: dict) -> str:
    if not zones:
        return "N/A"
    return max(zones, key=zones.get)


def predict_risk(density, speed, trend, acceleration, zones, flow_direction):
    """Rule-based congestion prediction with zone-specific reasons."""
    hottest = get_hottest_zone(zones)
    hottest_count = zones.get(hottest, 0) if zones else 0

    if density > 7 and speed < 30 and trend > 0:
        risk_level = "High"
        confidence = min(0.95, 0.7 + (density / 50) + (abs(trend) / 10))
        reason = (f"Dense crowd ({density:.1f}), slow movement ({speed:.1f} px/s), "
                  f"rising trend. Zone {hottest} critical ({hottest_count}p).")
    elif density > 4:
        risk_level = "Medium"
        confidence = min(0.90, 0.6 + (density / 30))
        reason = (f"Moderate density ({density:.1f}). "
                  f"Zone {hottest} busiest ({hottest_count}p). Flow: {flow_direction}.")
    else:
        risk_level = "Low"
        confidence = min(0.98, 0.8 + (1 / (density + 1)))
        reason = f"Low density ({density:.1f}). Area flowing normally ({flow_direction})."

    return risk_level, round(confidence, 3), reason


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": True, "xgboost": xgb_available}


@app.post("/predict", response_model=PredictionResponse)
def predict(data: CrowdData):
    global latest_prediction

    hottest_zone = get_hottest_zone(data.zones)

    risk_level, confidence, reason = predict_risk(
        data.density, data.speed, data.trend, data.acceleration,
        data.zones, data.flow_direction
    )

    result = {
        "density":        round(data.density, 2),
        "speed":          round(data.speed, 2),
        "trend":          round(data.trend, 3),
        "acceleration":   round(data.acceleration, 4),
        "zones":          data.zones,
        "hottest_zone":   hottest_zone,
        "flow_direction": data.flow_direction,
        "risk_level":     risk_level,
        "confidence":     confidence,
        "reason":         reason,
        "timestamp":      time.time(),
    }

    snapshot_store.append({
        "density": result["density"],
        "speed": result["speed"],
        "trend": result["trend"],
    })

    latest_prediction = result
    prediction_history.append(result)

    return PredictionResponse(**{k: v for k, v in result.items() if k != "timestamp"})


@app.get("/latest")
def get_latest():
    if latest_prediction:
        return latest_prediction
    return {"status": "no_data", "message": "No predictions yet. Run analytics.py to send data."}


@app.get("/history")
def get_history():
    return {"count": len(prediction_history), "data": list(prediction_history)}


@app.get("/zones")
def get_zones():
    if latest_prediction and latest_prediction.get("zones"):
        zones = latest_prediction["zones"]
        return {
            "zones":        zones,
            "hottest_zone": get_hottest_zone(zones),
            "total_people": sum(zones.values()),
            "timestamp":    latest_prediction.get("timestamp"),
        }
    return {"status": "no_data", "message": "No zone data yet."}


@app.get("/forecast")
def get_forecast():
    """XGBoost-based density & risk forecast using recent snapshots."""
    if not xgb_available:
        return {"status": "not_trained", "message": "Run: python backend/forecast.py"}

    if len(snapshot_store) < 2:
        return {"status": "insufficient_data", "message": "Need more snapshots. Keep analytics running."}

    result = predict_future(list(snapshot_store))
    if result is None:
        return {"status": "error", "message": "Forecast model could not generate prediction."}

    return {
        "status":            "ok",
        "predicted_density": result["predicted_density"],
        "predicted_risk":    result["predicted_risk"],
        "risk_confidence":   result["risk_confidence"],
        "based_on_snapshots": len(snapshot_store),
        "timestamp":         time.time(),
    }


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  URBAN PULSE AI - API Server v2.0")
    print("=" * 55)
    print("  Dashboard : http://localhost:8000")
    print("  API Docs  : http://localhost:8000/docs")
    print("  Latest    : http://localhost:8000/latest")
    print("  History   : http://localhost:8000/history")
    print("  Zones     : http://localhost:8000/zones")
    print("  Forecast  : http://localhost:8000/forecast")
    print("=" * 55)
    uvicorn.run(app, host="127.0.0.1", port=8000)