import os
import time
import joblib
import numpy as np
from collections import deque
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

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
latest_prediction = None

app = FastAPI(
    title="Urban Pulse AI",
    description="Crowd congestion prediction API",
    version="1.0.0",
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


class PredictionResponse(BaseModel):
    density: float
    speed: float
    trend: float
    acceleration: float
    risk_level: str
    confidence: float
    reason: str


def predict_risk(density, speed, trend, acceleration):
    """Rule-based congestion prediction."""
    if density > 7 and speed < 30 and trend > 0:
        risk_level = "High"
        confidence = min(0.95, 0.7 + (density / 50) + (abs(trend) / 10))
        reason = f"Dense crowd ({density:.1f}), slow movement ({speed:.1f} px/s), rising trend (+{trend:.2f}). Congestion imminent."
    elif density > 4:
        risk_level = "Medium"
        confidence = min(0.90, 0.6 + (density / 30))
        reason = f"Moderate density ({density:.1f}). Monitor for congestion buildup."
    else:
        risk_level = "Low"
        confidence = min(0.98, 0.8 + (1 / (density + 1)))
        reason = f"Low crowd density ({density:.1f}). Area is flowing normally."
    return risk_level, round(confidence, 3), reason


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": True}


@app.post("/predict", response_model=PredictionResponse)
def predict(data: CrowdData):
    global latest_prediction

    risk_level, confidence, reason = predict_risk(
        data.density, data.speed, data.trend, data.acceleration
    )

    result = {
        "density": round(data.density, 2),
        "speed": round(data.speed, 2),
        "trend": round(data.trend, 3),
        "acceleration": round(data.acceleration, 4),
        "risk_level": risk_level,
        "confidence": confidence,
        "reason": reason,
        "timestamp": time.time(),
    }

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


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  URBAN PULSE AI - API Server")
    print("=" * 55)
    print("  Dashboard : http://localhost:8000")
    print("  API Docs  : http://localhost:8000/docs")
    print("  Latest    : http://localhost:8000/latest")
    print("  History   : http://localhost:8000/history")
    print("=" * 55)
    uvicorn.run(app, host="127.0.0.1", port=8000)
