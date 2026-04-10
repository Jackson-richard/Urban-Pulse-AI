
from typing import Dict, List, Optional
from collections import deque
import time

ZONE_NEIGHBORS: Dict[str, List[str]] = {
    "A1": ["A2", "B1"],
    "A2": ["A1", "B2"],
    "B1": ["A1", "B2"],
    "B2": ["A2", "B1"],
}

ZONE_HIGH_THRESHOLD   = 4   
ZONE_MEDIUM_THRESHOLD = 2
DENSITY_HIGH          = 7.0
SPEED_LOW             = 30.0

def generate_route_recommendations(
    zones: Dict[str, int],
    density: float,
    speed: float,
    risk_level: str,
) -> List[Dict[str, str]]:
    if not zones:
        return []

    recommendations = []
    hottest_zone = max(zones, key=zones.get)
    hottest_count = zones[hottest_zone]

    neighbors = ZONE_NEIGHBORS.get(hottest_zone, [])
    coolest_neighbor = None
    coolest_count = float("inf")
    for n in neighbors:
        nc = zones.get(n, 0)
        if nc < coolest_count:
            coolest_count = nc
            coolest_neighbor = n

    if risk_level == "High":
        if coolest_neighbor and hottest_count > 0:
            redirect_pct = min(50, max(20, int((hottest_count - coolest_count) / hottest_count * 100)))
            recommendations.append({
                "action": f"Redirect {redirect_pct}% of crowd from {hottest_zone} to {coolest_neighbor}",
                "priority": "high",
                "icon": "🔀",
            })
        gate_zone = coolest_neighbor or neighbors[0] if neighbors else hottest_zone
        recommendations.append({
            "action": f"Open Gate {gate_zone} to relieve pressure on {hottest_zone}",
            "priority": "high",
            "icon": "🚪",
        })
        recommendations.append({
            "action": f"Deploy Staff to Zone {hottest_zone} immediately",
            "priority": "high",
            "icon": "👮",
        })

    elif risk_level == "Medium":
        if coolest_neighbor and hottest_count >= ZONE_MEDIUM_THRESHOLD:
            redirect_pct = min(35, max(15, int((hottest_count - coolest_count) / max(hottest_count, 1) * 100)))
            recommendations.append({
                "action": f"Redirect {redirect_pct}% of crowd from {hottest_zone} to {coolest_neighbor}",
                "priority": "medium",
                "icon": "🔀",
            })
        recommendations.append({
            "action": f"Monitor Zone {hottest_zone} closely — approaching threshold",
            "priority": "medium",
            "icon": "👁️",
        })
        if speed < 50:
            recommendations.append({
                "action": f"Pre-position Staff near Zone {hottest_zone}",
                "priority": "medium",
                "icon": "👮",
            })

    else:
        recommendations.append({
            "action": "No intervention needed — crowd flow is normal",
            "priority": "low",
            "icon": "✅",
        })

    return recommendations


zone_history: deque = deque(maxlen=30) 


def record_zone_snapshot(zones: Dict[str, int]) -> None:
    """Append a timestamped zone snapshot to the history buffer."""
    zone_history.append({
        "timestamp": time.time(),
        "zones": dict(zones),
    })


def predict_next_hot_zone(
    zones: Dict[str, int],
) -> Dict:
    if not zones:
        return {
            "predicted_next_hot_zone": "N/A",
            "estimated_time_to_congestion_minutes": None,
            "current_hottest": "N/A",
            "trend_summary": {},
            "confidence": 0.0,
        }

    current_hottest = max(zones, key=zones.get)

    if len(zone_history) < 3:
        return {
            "predicted_next_hot_zone": current_hottest,
            "estimated_time_to_congestion_minutes": None,
            "current_hottest": current_hottest,
            "trend_summary": {z: 0.0 for z in zones},
            "confidence": 0.3,
        }

    recent = list(zone_history)[-10:]  
    all_zones = list(zones.keys())
    trend_summary = {}
    growth_rates = {}

    for z in all_zones:
        counts = [snap["zones"].get(z, 0) for snap in recent]
        if len(counts) >= 2:
            trend = (counts[-1] - counts[0]) / len(counts)
            trend_summary[z] = round(trend, 2)
            growth_rates[z] = trend
        else:
            trend_summary[z] = 0.0
            growth_rates[z] = 0.0

    candidates = {z: rate for z, rate in growth_rates.items() if rate > 0}

    if not candidates:
        return {
            "predicted_next_hot_zone": current_hottest,
            "estimated_time_to_congestion_minutes": None,
            "current_hottest": current_hottest,
            "trend_summary": trend_summary,
            "confidence": 0.4,
        }

    # Prefer a zone that is NOT already the hottest but growing fast
    non_hot_candidates = {z: rate for z, rate in candidates.items() if z != current_hottest}
    if non_hot_candidates:
        predicted = max(non_hot_candidates, key=non_hot_candidates.get)
    else:
        predicted = max(candidates, key=candidates.get)

    current_count = zones.get(predicted, 0)
    rate = growth_rates.get(predicted, 0)
    remaining = ZONE_HIGH_THRESHOLD - current_count

    if rate > 0 and remaining > 0:
        snapshots_needed = remaining / rate
        if len(recent) >= 2:
            avg_interval_sec = (recent[-1]["timestamp"] - recent[0]["timestamp"]) / (len(recent) - 1)
        else:
            avg_interval_sec = 2.0
        minutes = (snapshots_needed * avg_interval_sec) / 60.0
        estimated_minutes = round(max(0.1, minutes), 1)
    elif remaining <= 0:
        estimated_minutes = 0.0  
    else:
        estimated_minutes = None

    confidence = min(0.95, 0.4 + (len(zone_history) / 30) * 0.5)

    return {
        "predicted_next_hot_zone": predicted,
        "estimated_time_to_congestion_minutes": estimated_minutes,
        "current_hottest": current_hottest,
        "trend_summary": trend_summary,
        "confidence": round(confidence, 2),
    }


def generate_risk_explanation(
    density: float,
    speed: float,
    trend: float,
    acceleration: float,
    zones: Dict[str, int],
    risk_level: str,
    confidence: float,
) -> Dict:
    
    factors = []

    if density > DENSITY_HIGH:
        factors.append({
            "factor": "density",
            "detail": f"Density at {density:.1f} — exceeds threshold ({DENSITY_HIGH})",
            "impact": "high",
            "icon": "📈",
        })
    elif density > DENSITY_HIGH * 0.6:
        factors.append({
            "factor": "density",
            "detail": f"Density at {density:.1f} — approaching threshold ({DENSITY_HIGH})",
            "impact": "medium",
            "icon": "📊",
        })
    else:
        factors.append({
            "factor": "density",
            "detail": f"Density at {density:.1f} — well below threshold ({DENSITY_HIGH})",
            "impact": "low",
            "icon": "📉",
        })

    if speed < SPEED_LOW:
        factors.append({
            "factor": "speed",
            "detail": f"Speed dropped to {speed:.1f} px/s — below {SPEED_LOW} px/s",
            "impact": "high",
            "icon": "🐢",
        })
    elif speed < SPEED_LOW * 2:
        factors.append({
            "factor": "speed",
            "detail": f"Speed at {speed:.1f} px/s — moderate crowd movement",
            "impact": "medium",
            "icon": "🚶",
        })
    else:
        factors.append({
            "factor": "speed",
            "detail": f"Speed at {speed:.1f} px/s — crowd is flowing freely",
            "impact": "low",
            "icon": "🏃",
        })

    
    if trend > 1.0:
        pct = trend * 10  
        factors.append({
            "factor": "trend",
            "detail": f"Density increasing (+{pct:.0f}% trend) — crowd is building up",
            "impact": "high",
            "icon": "⬆️",
        })
    elif trend > 0:
        factors.append({
            "factor": "trend",
            "detail": f"Slight upward trend (+{trend:.2f}) — gradual increase",
            "impact": "medium",
            "icon": "↗️",
        })
    elif trend < -0.5:
        factors.append({
            "factor": "trend",
            "detail": f"Density declining ({trend:.2f}) — crowd is dispersing",
            "impact": "low",
            "icon": "⬇️",
        })
    else:
        factors.append({
            "factor": "trend",
            "detail": f"Trend stable ({trend:+.2f}) — no significant change",
            "impact": "low",
            "icon": "➡️",
        })

    if abs(acceleration) > 0.5:
        direction = "accelerating" if acceleration > 0 else "decelerating"
        imp = "high" if acceleration > 0 else "medium"
        factors.append({
            "factor": "acceleration",
            "detail": f"Crowd {direction} ({acceleration:+.3f}) — rapid change detected",
            "impact": imp,
            "icon": "⚡",
        })

    
    if zones:
        hottest = max(zones, key=zones.get)
        hottest_count = zones[hottest]
        total = sum(zones.values())
        if total > 0 and hottest_count >= ZONE_HIGH_THRESHOLD:
            pct_in_hot = (hottest_count / total * 100)
            factors.append({
                "factor": "zone_concentration",
                "detail": f"Zone {hottest} has {hottest_count} people ({pct_in_hot:.0f}% of total) — threshold exceeded",
                "impact": "high",
                "icon": "🔥",
            })
        elif hottest_count >= ZONE_MEDIUM_THRESHOLD:
            factors.append({
                "factor": "zone_concentration",
                "detail": f"Zone {hottest} has {hottest_count} people — moderate concentration",
                "impact": "medium",
                "icon": "📍",
            })

    high_count = sum(1 for f in factors if f["impact"] == "high")
    medium_count = sum(1 for f in factors if f["impact"] == "medium")

    if high_count >= 2:
        summary = f"{high_count} high-impact factors detected. Immediate intervention recommended."
    elif high_count == 1:
        summary = f"1 high-impact factor detected with {medium_count} medium concerns. Monitor closely."
    elif medium_count >= 2:
        summary = f"{medium_count} medium-impact factors detected. Stay vigilant."
    else:
        summary = "All indicators within normal range. No action required."

    return {
        "risk_level": risk_level,
        "confidence": confidence,
        "factors": factors,
        "summary": summary,
        "threshold_status": {
            "density_threshold": DENSITY_HIGH,
            "density_exceeded": density > DENSITY_HIGH,
            "speed_threshold": SPEED_LOW,
            "speed_below": speed < SPEED_LOW,
        },
    }
