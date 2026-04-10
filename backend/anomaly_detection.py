
from typing import Dict, List, Optional
from collections import deque
import numpy as np
import time

SPEED_SPIKE_FACTOR = 2.5      
SPEED_SPIKE_MIN_THRESHOLD = 80  
DIRECTION_VARIANCE_THRESHOLD = 90  
REVERSE_FLOW_PERCENTAGE = 40 
MIN_PEOPLE_FOR_ANOMALY = 3

_speed_history: deque = deque(maxlen=30)     
_anomaly_history: deque = deque(maxlen=20)    


def _record_speed(speed: float) -> None:
    
    _speed_history.append({
        "speed": speed,
        "timestamp": time.time(),
    })


def detect_anomalies(
    avg_speed: float,
    individual_angles: List[float],
    prev_dominant_angle: Optional[float],
    people_count: int,
) -> Dict:
    _record_speed(avg_speed)
    if people_count < MIN_PEOPLE_FOR_ANOMALY:
        return _no_anomaly("Insufficient tracked people for anomaly detection")

    speed_anomaly = _check_speed_spike(avg_speed)
    if speed_anomaly["detected"]:
        event = {
            "anomaly_detected": True,
            "anomaly_type": "panic_rush",
            "anomaly_confidence": speed_anomaly["confidence"],
            "anomaly_reason": speed_anomaly["reason"],
            "anomaly_severity": "critical",
            "anomaly_icon": "🚨",
            "details": speed_anomaly,
        }
        _anomaly_history.append({**event, "timestamp": time.time()})
        return event

    chaos_anomaly = _check_chaotic_movement(individual_angles)
    if chaos_anomaly["detected"]:
        event = {
            "anomaly_detected": True,
            "anomaly_type": "chaotic_movement",
            "anomaly_confidence": chaos_anomaly["confidence"],
            "anomaly_reason": chaos_anomaly["reason"],
            "anomaly_severity": "warning",
            "anomaly_icon": "⚠️",
            "details": chaos_anomaly,
        }
        _anomaly_history.append({**event, "timestamp": time.time()})
        return event

    reverse_anomaly = _check_reverse_flow(individual_angles, prev_dominant_angle)
    if reverse_anomaly["detected"]:
        event = {
            "anomaly_detected": True,
            "anomaly_type": "reverse_flow",
            "anomaly_confidence": reverse_anomaly["confidence"],
            "anomaly_reason": reverse_anomaly["reason"],
            "anomaly_severity": "warning",
            "anomaly_icon": "🔄",
            "details": reverse_anomaly,
        }
        _anomaly_history.append({**event, "timestamp": time.time()})
        return event

    return _no_anomaly("All crowd movement within normal parameters")


def _no_anomaly(reason: str = "") -> Dict:
    return {
        "anomaly_detected": False,
        "anomaly_type": "none",
        "anomaly_confidence": 0.0,
        "anomaly_reason": reason,
        "anomaly_severity": "none",
        "anomaly_icon": "✅",
        "details": {},
    }


def _check_speed_spike(current_speed: float) -> Dict:
    if len(_speed_history) < 5:
        return {"detected": False}
    recent_speeds = [s["speed"] for s in list(_speed_history)[:-1]]
    rolling_avg = np.mean(recent_speeds)
    rolling_std = np.std(recent_speeds) if len(recent_speeds) > 2 else 0
    if rolling_avg <= 0:
        return {"detected": False}

    spike_ratio = current_speed / rolling_avg

    if (spike_ratio >= SPEED_SPIKE_FACTOR and
            current_speed >= SPEED_SPIKE_MIN_THRESHOLD):
        confidence = min(0.95, 0.5 + (spike_ratio - SPEED_SPIKE_FACTOR) * 0.15)
        return {
            "detected": True,
            "confidence": round(confidence, 2),
            "reason": (f"Possible Panic / Rush Event — speed surged to "
                       f"{current_speed:.0f} px/s ({spike_ratio:.1f}× above "
                       f"recent average of {rolling_avg:.0f} px/s)"),
            "current_speed": round(current_speed, 1),
            "rolling_average": round(rolling_avg, 1),
            "spike_ratio": round(spike_ratio, 2),
        }

    return {"detected": False}


def _check_chaotic_movement(angles: List[float]) -> Dict:
    if len(angles) < MIN_PEOPLE_FOR_ANOMALY:
        return {"detected": False}
    angles_rad = np.radians(angles)
    mean_sin = np.mean(np.sin(angles_rad))
    mean_cos = np.mean(np.cos(angles_rad))
    R = np.sqrt(mean_sin**2 + mean_cos**2)  
    if R > 0 and R < 1:
        circ_std_deg = np.degrees(np.sqrt(-2 * np.log(R)))
    elif R >= 1:
        circ_std_deg = 0
    else:
        circ_std_deg = 180  # maximum chaos

    if circ_std_deg >= DIRECTION_VARIANCE_THRESHOLD:
        confidence = min(0.90, 0.4 + (circ_std_deg - DIRECTION_VARIANCE_THRESHOLD) / 100)
        return {
            "detected": True,
            "confidence": round(confidence, 2),
            "reason": (f"Chaotic Crowd Movement — directional variance at "
                       f"{circ_std_deg:.0f}° (threshold: {DIRECTION_VARIANCE_THRESHOLD}°). "
                       f"People moving in highly scattered directions."),
            "directional_variance": round(circ_std_deg, 1),
            "alignment_score": round(R, 3),
        }

    return {"detected": False}


def _check_reverse_flow(
    angles: List[float],
    prev_dominant: Optional[float],
) -> Dict:

    if not angles or len(angles) < MIN_PEOPLE_FOR_ANOMALY or prev_dominant is None:
        return {"detected": False}
    reverse_count = 0
    for angle in angles:
        diff = abs(angle - prev_dominant) % 360
        if diff > 180:
            diff = 360 - diff
        if diff > 120:
            reverse_count += 1

    reverse_pct = (reverse_count / len(angles)) * 100

    if reverse_pct >= REVERSE_FLOW_PERCENTAGE:
        confidence = min(0.88, 0.4 + (reverse_pct - REVERSE_FLOW_PERCENTAGE) / 80)
        return {
            "detected": True,
            "confidence": round(confidence, 2),
            "reason": (f"Reverse Crowd Flow Detected — {reverse_pct:.0f}% of tracked "
                       f"people ({reverse_count}/{len(angles)}) moving opposite "
                       f"to dominant flow direction."),
            "reverse_percentage": round(reverse_pct, 1),
            "reverse_count": reverse_count,
            "total_tracked": len(angles),
        }

    return {"detected": False}


def get_anomaly_history() -> List[Dict]:
    """Return recent anomaly events for dashboard display."""
    return list(_anomaly_history)
