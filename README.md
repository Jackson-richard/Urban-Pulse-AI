# 🏙️ Urban Pulse AI
### Crowd Flow & Congestion Prediction System

> Real-time crowd detection, tracking, and congestion risk prediction using computer vision and machine learning.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![YOLO](https://img.shields.io/badge/YOLOv8-Detection-green?logo=yolo)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-teal?logo=fastapi)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-orange?logo=scikit-learn)

---

## 🎯 What It Does

1. **Detects people** in video using YOLOv8 (pretrained, no training needed)
2. **Tracks people** across frames using DeepSORT (unique IDs per person)
3. **Calculates** crowd density and movement speed
4. **Predicts congestion risk** (Low/Medium/High) using a trained ML model
5. **Displays results** in a live web dashboard

---

## 📁 Project Structure

```
urban pulse AI/
├── backend/
│   ├── detect.py          # Step 1: YOLO person detection
│   ├── tracker.py         # Step 2: DeepSORT person tracking
│   ├── analytics.py       # Step 3+5: Full analysis + API integration
│   ├── train_model.py     # Step 4a: Train congestion ML model
│   └── api.py             # Step 4b: FastAPI server
├── frontend/
│   ├── index.html         # Dashboard page
│   ├── style.css          # Dashboard styles
│   └── script.js          # Live polling + charts
├── models/
│   └── congestion_model.joblib  # Trained ML model
├── data/
│   └── video.mp4          # Test video (you provide)
├── .gitignore
├── requirements.txt
├── start.ps1              # One-click startup
└── README.md
```

---

## 🚀 Quick Start

### 1. Setup
```powershell
cd "urban pulse AI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Train the ML model
```powershell
python backend/train_model.py
```

### 3. Start everything
```powershell
.\start.ps1
```

Or manually:
```powershell
# Terminal 1: Start API + Dashboard
python backend/api.py

# Terminal 2: Run video analytics
python backend/analytics.py --source 0          # webcam
python backend/analytics.py --source data/video.mp4  # video file
```

### 4. Open the dashboard
```
http://localhost:8000
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Detection | YOLOv8 (ultralytics) |
| Tracking | DeepSORT (deep-sort-realtime) |
| Backend API | FastAPI + Uvicorn |
| ML Model | Random Forest (scikit-learn) |
| Frontend | HTML/CSS/JS + Chart.js |
| Video Processing | OpenCV |

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger API docs |
| POST | `/predict` | Get congestion prediction |
| GET | `/latest` | Latest prediction result |
| GET | `/history` | Prediction history (last 100) |

### POST /predict
```json
// Request
{"density": 8.5, "speed": 25.0}

// Response
{
  "density": 8.5,
  "speed": 25.0,
  "risk_level": "High",
  "confidence": 0.95,
  "reason": "High density combined with slow movement indicates congestion."
}
```

---

## 🧮 How It Works

```
Video/Webcam → YOLOv8 Detection → DeepSORT Tracking
                                        ↓
                              density + speed calculated
                                        ↓
                              POST /predict → ML Model
                                        ↓
                              {risk_level, confidence, reason}
                                        ↓
                              Dashboard (live updates)
```

### Metrics:
- **Density** = `people_count / frame_area × 1,000,000` (people per megapixel)
- **Speed** = average pixel displacement per second (tracked via DeepSORT IDs)
- **Risk Level** = Low / Medium / High (Random Forest trained on synthetic data)

---

## 📝 License

Hackathon project — free to use and modify.
