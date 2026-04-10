import os
import sys
import time
import joblib
import numpy as np
from collections import deque
from typing import Dict, List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from forecast import load_forecast_models, predict_future
from advanced_analytics import (
    generate_route_recommendations,
    record_zone_snapshot,
    predict_next_hot_zone,
    generate_risk_explanation,
)
from anomaly_detection import detect_anomalies, get_anomaly_history
from deployment_config import (
    get_deployment_config,
    update_deployment_toggle,
    get_realworld_metrics,
    get_calibration_params,
    update_calibration_params,
    get_active_modes_summary,
)

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
    description="Crowd congestion prediction with anomaly detection, deployment config, camera calibration, zone analytics, XGBoost forecasting, route recommendations, spatiotemporal forecasting, and explainable AI",
    version="4.0.0",
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
    individual_angles: List[float] = []      
    prev_dominant_angle: Optional[float] = None  
    people_count: int = 0                    


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
    route_recommendations: List[Dict] = []
    risk_explanation: Dict = {}
    spatiotemporal: Dict = {}
    anomaly: Dict = {}
    realworld_metrics: Dict = {}


def get_hottest_zone(zones: dict) -> str:
    if not zones:
        return "N/A"
    return max(zones, key=zones.get)


def predict_risk(density, speed, trend, acceleration, zones, flow_direction):
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

    route_recs = generate_route_recommendations(
        zones=data.zones,
        density=data.density,
        speed=data.speed,
        risk_level=risk_level,
    )

    record_zone_snapshot(data.zones)
    spatiotemporal = predict_next_hot_zone(data.zones)

    risk_explanation = generate_risk_explanation(
        density=data.density,
        speed=data.speed,
        trend=data.trend,
        acceleration=data.acceleration,
        zones=data.zones,
        risk_level=risk_level,
        confidence=confidence,
    )

    anomaly = detect_anomalies(
        avg_speed=data.speed,
        individual_angles=data.individual_angles,
        prev_dominant_angle=data.prev_dominant_angle,
        people_count=data.people_count,
    )

    realworld = get_realworld_metrics(data.density, data.speed)

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
        "route_recommendations": route_recs,
        "risk_explanation":      risk_explanation,
        "spatiotemporal":        spatiotemporal,
        "anomaly":               anomaly,
        "realworld_metrics":     realworld,
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


@app.get("/advanced")
def get_advanced():
    """Return route recommendations + explainable AI + anomaly data from latest prediction."""
    if latest_prediction:
        return {
            "status": "ok",
            "route_recommendations": latest_prediction.get("route_recommendations", []),
            "risk_explanation":      latest_prediction.get("risk_explanation", {}),
            "anomaly":               latest_prediction.get("anomaly", {}),
            "realworld_metrics":     latest_prediction.get("realworld_metrics", {}),
            "timestamp":             latest_prediction.get("timestamp"),
        }
    return {"status": "no_data", "message": "No predictions yet."}


@app.get("/spatiotemporal")
def get_spatiotemporal():
    """Return spatiotemporal zone congestion forecast."""
    if latest_prediction:
        return {
            "status": "ok",
            "spatiotemporal": latest_prediction.get("spatiotemporal", {}),
            "timestamp":     latest_prediction.get("timestamp"),
        }
    return {"status": "no_data", "message": "No predictions yet."}


@app.get("/anomaly")
def get_anomaly():
    """Return current anomaly status + recent anomaly history."""
    current = latest_prediction.get("anomaly", {}) if latest_prediction else {}
    return {
        "status": "ok",
        "current": current,
        "history": get_anomaly_history(),
    }


@app.get("/config")
def get_config():
    """Return deployment configuration and deployment readiness status."""
    return {
        "status": "ok",
        "config": get_deployment_config(),
        "active_modes": get_active_modes_summary(),
    }


class ToggleRequest(BaseModel):
    key: str
    enabled: bool


@app.post("/config/toggle")
def toggle_config(req: ToggleRequest):
    """Toggle a deployment configuration setting."""
    result = update_deployment_toggle(req.key, req.enabled)
    return {
        "status": "ok" if "error" not in result else "error",
        "config": result,
        "active_modes": get_active_modes_summary(),
    }


@app.get("/calibration")
def get_calibration():
    """Return current camera calibration parameters."""
    return {
        "status": "ok",
        "params": get_calibration_params(),
    }


class CalibrationRequest(BaseModel):
    pixels_per_meter_x: Optional[float] = None
    pixels_per_meter_y: Optional[float] = None
    camera_height: Optional[float] = None
    perspective_factor: Optional[float] = None


@app.post("/calibration")
def set_calibration(req: CalibrationRequest):
    """Update camera calibration parameters."""
    params = {k: v for k, v in req.dict().items() if v is not None}
    updated = update_calibration_params(params)
    return {"status": "ok", "params": updated}


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  URBAN PULSE AI - API Server v4.0")
    print("=" * 55)
    print("  Dashboard      : http://localhost:8000")
    print("  API Docs       : http://localhost:8000/docs")
    print("  Latest         : http://localhost:8000/latest")
    print("  History        : http://localhost:8000/history")
    print("  Zones          : http://localhost:8000/zones")
    print("  Forecast       : http://localhost:8000/forecast")
    print("  Advanced       : http://localhost:8000/advanced")
    print("  Spatiotemporal : http://localhost:8000/spatiotemporal")
    print("  Anomaly        : http://localhost:8000/anomaly")
    print("  Config         : http://localhost:8000/config")
    print("  Calibration    : http://localhost:8000/calibration")
    print("=" * 55)
    uvicorn.run(app, host="127.0.0.1", port=8000)