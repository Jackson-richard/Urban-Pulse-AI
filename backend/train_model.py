import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


def generate_synthetic_data(n_samples=2000):
    """
    Generate synthetic crowd data with 3 risk levels:
      0 = Low    → low density, any speed
      1 = Medium → moderate density, moderate speed
      2 = High   → high density OR very low speed (gridlock)
    """
    np.random.seed(42)

    densities = []
    speeds = []
    labels = []

    # LOW RISK: few people, moving freely
    n_low = n_samples // 3
    densities.append(np.random.uniform(0, 3, n_low))
    speeds.append(np.random.uniform(50, 300, n_low))
    labels.append(np.zeros(n_low, dtype=int))

    # MEDIUM RISK: moderate crowd, slowing down
    n_med = n_samples // 3
    densities.append(np.random.uniform(2, 7, n_med))
    speeds.append(np.random.uniform(20, 150, n_med))
    labels.append(np.ones(n_med, dtype=int))

    # HIGH RISK: dense crowd, barely moving
    n_high = n_samples - n_low - n_med
    densities.append(np.random.uniform(5, 15, n_high))
    speeds.append(np.random.uniform(0, 60, n_high))
    labels.append(np.full(n_high, 2, dtype=int))

    X = np.column_stack([
        np.concatenate(densities),
        np.concatenate(speeds),
    ])
    y = np.concatenate(labels)

    # Shuffle
    shuffle_idx = np.random.permutation(len(y))
    X = X[shuffle_idx]
    y = y[shuffle_idx]

    return X, y


def train_and_save():
    print("=" * 50)
    print("  URBAN PULSE AI - Model Training")
    print("=" * 50)

    # Generate data
    print("\n[1/4] Generating synthetic training data...")
    X, y = generate_synthetic_data(2000)
    print(f"       Total samples: {len(y)}")
    print(f"       Features: density, speed")
    print(f"       Classes: Low(0)={sum(y==0)}, Medium(1)={sum(y==1)}, High(2)={sum(y==2)}")

    # Split
    print("\n[2/4] Splitting into train/test (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"       Train: {len(X_train)} | Test: {len(X_test)}")

    # Train
    print("\n[3/4] Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    accuracy = model.score(X_test, y_test)
    print(f"       Accuracy: {accuracy:.1%}")
    print()
    print(classification_report(
        y_test, model.predict(X_test),
        target_names=["Low", "Medium", "High"]
    ))

    # Save model
    print("[4/4] Saving model...")
    model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "congestion_model.joblib")
    joblib.dump(model, model_path)
    print(f"       Saved to: {os.path.abspath(model_path)}")

    print()
    print("=" * 50)
    print("  MODEL TRAINING COMPLETE")
    print("=" * 50)

    # Quick test predictions
    print("\n  Quick test predictions:")
    test_cases = [
        (1.0, 200.0, "Few people, moving fast"),
        (4.0, 80.0, "Moderate crowd, moderate speed"),
        (10.0, 15.0, "Dense crowd, barely moving"),
    ]
    risk_names = ["Low", "Medium", "High"]

    for density, speed, desc in test_cases:
        pred = model.predict([[density, speed]])[0]
        proba = model.predict_proba([[density, speed]])[0]
        conf = max(proba)
        print(f"    density={density:.1f}, speed={speed:.1f} → {risk_names[pred]} ({conf:.0%}) | {desc}")

    print()


if __name__ == "__main__":
    train_and_save()
