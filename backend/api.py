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

# Store prediction history (last 100 entries)
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


class PredictionResponse(BaseModel):
    density: float
    speed: float
    risk_level: str
    confidence: float
    reason: str


def generate_reason(density, speed, risk_level):
    if risk_level == "High":
        if speed < 20:
            return "Very dense crowd with near-zero movement. Potential gridlock."
        elif density > 8:
            return "Extremely high crowd density detected. Movement severely restricted."
        else:
            return "High density combined with slow movement indicates congestion."
    elif risk_level == "Medium":
        if speed < 50:
            return "Moderate crowd density with reduced movement speed."
        else:
            return "Growing crowd density. Movement still possible but slowing."
    else:
        if density < 1:
            return "Very few people detected. Area is clear."
        else:
            return "Low crowd density with normal movement speed. No congestion risk."


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": True}


@app.post("/predict", response_model=PredictionResponse)
def predict(data: CrowdData):
    global latest_prediction

    features = np.array([[data.density, data.speed]])
    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    confidence = float(max(probabilities))
    risk_level = RISK_LABELS[prediction]
    reason = generate_reason(data.density, data.speed, risk_level)

    result = {
        "density": round(data.density, 2),
        "speed": round(data.speed, 2),
        "risk_level": risk_level,
        "confidence": round(confidence, 3),
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


# Serve frontend static files
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
