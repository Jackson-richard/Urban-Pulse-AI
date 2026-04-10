import os
import numpy as np
import joblib
from xgboost import XGBRegressor, XGBClassifier


MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
DENSITY_MODEL_PATH = os.path.join(MODEL_DIR, "xgb_density_forecast.joblib")
RISK_MODEL_PATH = os.path.join(MODEL_DIR, "xgb_risk_forecast.joblib")

RISK_LABELS = ["Low", "Medium", "High"]


def generate_synthetic_timeseries(n_sequences=3000, window=5):
    X, y_density, y_risk = [], [], []

    for _ in range(n_sequences):
        scenario = np.random.choice(["calm", "building", "congested", "dispersing"])

        if scenario == "calm":
            densities = np.random.uniform(0, 3, window) + np.random.normal(0, 0.3, window)
            speeds = np.random.uniform(80, 250, window) + np.random.normal(0, 10, window)
            future_density = np.random.uniform(0, 3)
            risk = 0
        elif scenario == "building":
            base = np.random.uniform(2, 5)
            densities = base + np.linspace(0, 4, window) + np.random.normal(0, 0.3, window)
            speeds = np.linspace(150, 50, window) + np.random.normal(0, 10, window)
            future_density = densities[-1] + np.random.uniform(1, 3)
            risk = 1 if future_density < 7 else 2
        elif scenario == "congested":
            densities = np.random.uniform(6, 15, window) + np.random.normal(0, 0.5, window)
            speeds = np.random.uniform(5, 40, window) + np.random.normal(0, 5, window)
            future_density = np.random.uniform(7, 15)
            risk = 2
        else:  
            base = np.random.uniform(5, 10)
            densities = base - np.linspace(0, 4, window) + np.random.normal(0, 0.3, window)
            speeds = np.linspace(30, 150, window) + np.random.normal(0, 10, window)
            future_density = max(0, densities[-1] - np.random.uniform(1, 3))
            risk = 0 if future_density < 3 else 1

        densities = np.clip(densities, 0, 20)
        speeds = np.clip(speeds, 0, 300)
        future_density = np.clip(future_density, 0, 20)

        trend = densities[-1] - densities[0]
        accel = trend / window

        features = []
        for i in range(window):
            features.extend([densities[i], speeds[i]])
        features.extend([trend, accel])

        X.append(features)
        y_density.append(future_density)
        y_risk.append(risk)

    return np.array(X), np.array(y_density), np.array(y_risk)


def train_forecast_models():
    """Train XGBoost models for density forecasting and risk classification."""
    print("=" * 55)
    print("  URBAN PULSE AI — XGBoost Forecast Training")
    print("=" * 55)

    print("\n[1/3] Generating synthetic time-series data...")
    X, y_density, y_risk = generate_synthetic_timeseries(n_sequences=5000, window=5)
    print(f"       Samples: {len(X)}, Features per sample: {X.shape[1]}")

    print("\n[2/3] Training XGBoost density regressor...")
    density_model = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    density_model.fit(X, y_density)
    density_score = density_model.score(X, y_density)
    print(f"       R² Score: {density_score:.3f}")

    print("       Training XGBoost risk classifier...")
    risk_model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric="mlogloss",
    )
    risk_model.fit(X, y_risk)
    risk_score = risk_model.score(X, y_risk)
    print(f"       Accuracy: {risk_score:.1%}")

    print("\n[3/3] Saving models...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(density_model, DENSITY_MODEL_PATH)
    joblib.dump(risk_model, RISK_MODEL_PATH)
    print(f"       → {DENSITY_MODEL_PATH}")
    print(f"       → {RISK_MODEL_PATH}")

    print("\n" + "=" * 55)
    print("  XGBoost FORECAST TRAINING COMPLETE")
    print("=" * 55)

    print("\n  Quick test predictions:")
    test_cases = [
        ("Calm crowd",      [1,200, 1,210, 1,190, 1,200, 1,195, 0, 0]),
        ("Building up",     [2,150, 3,120, 4,90,  5,60,  6,40,  4, 0.8]),
        ("Congested",       [10,20, 11,15, 12,10, 12,8,  13,5,  3, 0.6]),
        ("Dispersing",      [8,30,  7,50,  6,80,  5,100, 4,130, -4,-0.8]),
    ]
    for name, features in test_cases:
        X_test = np.array([features])
        pred_density = density_model.predict(X_test)[0]
        pred_risk_idx = risk_model.predict(X_test)[0]
        pred_risk_proba = risk_model.predict_proba(X_test)[0]
        print(f"    {name:20s} → Density: {pred_density:.1f}, "
              f"Risk: {RISK_LABELS[pred_risk_idx]} ({max(pred_risk_proba):.0%})")


def load_forecast_models():
    """Load trained XGBoost models. Returns (density_model, risk_model) or (None, None)."""
    if os.path.exists(DENSITY_MODEL_PATH) and os.path.exists(RISK_MODEL_PATH):
        return joblib.load(DENSITY_MODEL_PATH), joblib.load(RISK_MODEL_PATH)
    return None, None


def predict_future(snapshots, window=5):
    density_model, risk_model = load_forecast_models()
    if density_model is None or risk_model is None:
        return None

    if len(snapshots) < window:
        padded = [snapshots[0]] * (window - len(snapshots)) + list(snapshots)
    else:
        padded = list(snapshots[-window:])

    features = []
    for s in padded:
        features.extend([s.get("density", 0), s.get("speed", 0)])

    densities = [s.get("density", 0) for s in padded]
    trend = densities[-1] - densities[0]
    accel = trend / window
    features.extend([trend, accel])

    X = np.array([features])
    pred_density = float(density_model.predict(X)[0])
    pred_risk_idx = int(risk_model.predict(X)[0])
    pred_risk_proba = risk_model.predict_proba(X)[0]
    confidence = float(max(pred_risk_proba))

    return {
        "predicted_density": round(max(0, pred_density), 2),
        "predicted_risk": RISK_LABELS[pred_risk_idx],
        "risk_confidence": round(confidence, 3),
    }


if __name__ == "__main__":
    train_forecast_models()
