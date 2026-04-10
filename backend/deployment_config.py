from typing import Dict, Optional
import time
_deployment_config: Dict = {
    "edge_mode": False,
    "low_bandwidth_mode": False,
    "night_mode": False,
    "camera_calibration_enabled": False,
}

DEPLOYMENT_TOGGLE_META = {
    "edge_mode": {
        "label": "Edge Device Mode",
        "icon": "🔲",
        "description": "Optimized for Jetson Nano / RPi — reduces model size and resolution",
    },
    "low_bandwidth_mode": {
        "label": "Low Bandwidth",
        "icon": "📡",
        "description": "Reduces API payload frequency and disables heavy data transfers",
    },
    "night_mode": {
        "label": "Night / IR Mode",
        "icon": "🌙",
        "description": "Adjusts detection for low-light and infrared camera feeds",
    },
    "camera_calibration_enabled": {
        "label": "Camera Calibration",
        "icon": "📐",
        "description": "Enables pixel-to-meter conversion using calibration parameters",
    },
}


def get_deployment_config() -> Dict:
    """Return current deployment configuration with metadata."""
    toggles = []
    for key, value in _deployment_config.items():
        meta = DEPLOYMENT_TOGGLE_META.get(key, {})
        toggles.append({
            "key": key,
            "enabled": value,
            "label": meta.get("label", key),
            "icon": meta.get("icon", "⚙️"),
            "description": meta.get("description", ""),
        })
    return {
        "toggles": toggles,
        "active_count": sum(1 for v in _deployment_config.values() if v),
        "total_count": len(_deployment_config),
    }


def update_deployment_toggle(key: str, enabled: bool) -> Dict:
    """Update a single deployment toggle. Returns the updated config."""
    if key not in _deployment_config:
        return {"error": f"Unknown config key: {key}"}
    _deployment_config[key] = enabled
    return get_deployment_config()


def is_calibration_enabled() -> bool:
    return _deployment_config.get("camera_calibration_enabled", False)


def get_active_modes_summary() -> str:
    """Human-readable summary of active deployment modes."""
    active = [DEPLOYMENT_TOGGLE_META[k]["label"]
              for k, v in _deployment_config.items() if v]
    if not active:
        return "Standard Mode"
    return " + ".join(active)

_calibration_params: Dict = {
    "pixels_per_meter_x": 50.0,
    "pixels_per_meter_y": 45.0,
    "camera_height": 4.0,
    "perspective_factor": 0.85,
}


def get_calibration_params() -> Dict:
    return dict(_calibration_params)


def update_calibration_params(params: Dict) -> Dict:
    for key, value in params.items():
        if key in _calibration_params:
            _calibration_params[key] = float(value)
    return get_calibration_params()


def convert_speed_to_meters(speed_px_per_sec: float) -> float:
    avg_ppm = (_calibration_params["pixels_per_meter_x"] +
               _calibration_params["pixels_per_meter_y"]) / 2.0
    if avg_ppm <= 0:
        return 0.0
    return round(speed_px_per_sec / avg_ppm * _calibration_params["perspective_factor"], 3)


def convert_density_to_sqm(density_ppl_per_mpx: float,
                            frame_width: int = 1920,
                            frame_height: int = 1080) -> float:
    ppm_x = _calibration_params["pixels_per_meter_x"]
    ppm_y = _calibration_params["pixels_per_meter_y"]
    pf = _calibration_params["perspective_factor"]

    if ppm_x <= 0 or ppm_y <= 0:
        return 0.0

    frame_pixels = frame_width * frame_height
    people_in_frame = density_ppl_per_mpx * (frame_pixels / 1_000_000)

    ground_width_m = frame_width / ppm_x
    ground_height_m = frame_height / ppm_y
    ground_area_m2 = ground_width_m * ground_height_m * (pf ** 2)

    if ground_area_m2 <= 0:
        return 0.0

    return round(people_in_frame / ground_area_m2, 4)


def get_realworld_metrics(density: float, speed: float) -> Dict:

    speed_ms = convert_speed_to_meters(speed)
    density_sqm = convert_density_to_sqm(density)

    if speed_ms > 2.0:
        speed_context = "Running pace"
    elif speed_ms > 1.0:
        speed_context = "Normal walking"
    elif speed_ms > 0.3:
        speed_context = "Slow shuffle"
    elif speed_ms > 0:
        speed_context = "Near stationary"
    else:
        speed_context = "Stationary"

    if density_sqm <= 0:
        density_context = "No crowd"
        los_grade = "A"
    elif density_sqm < 0.5:
        density_context = "Free flow"
        los_grade = "A"
    elif density_sqm < 1.0:
        density_context = "Comfortable"
        los_grade = "B"
    elif density_sqm < 2.0:
        density_context = "Moderate crowd"
        los_grade = "C"
    elif density_sqm < 3.5:
        density_context = "Dense crowd"
        los_grade = "D"
    elif density_sqm < 5.0:
        density_context = "Very dense"
        los_grade = "E"
    else:
        density_context = "Crush risk"
        los_grade = "F"

    return {
        "calibration_enabled": is_calibration_enabled(),
        "speed_m_s": speed_ms,
        "speed_km_h": round(speed_ms * 3.6, 2),
        "speed_context": speed_context,
        "density_per_sqm": density_sqm,
        "density_context": density_context,
        "level_of_service": los_grade,
        "calibration_params": get_calibration_params(),
    }
