import argparse
import time
import cv2
import numpy as np
import requests
from collections import deque
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort


API_URL = "http://localhost:8000/predict"

feature_store = deque(maxlen=20)
last_snapshot_time = time.time()
SNAPSHOT_INTERVAL = 30


def get_color(track_id):
    np.random.seed(track_id * 42)
    return tuple(int(c) for c in np.random.randint(100, 255, size=3))


def calculate_density(people_count, frame_width, frame_height):
    frame_area = frame_width * frame_height
    if frame_area == 0:
        return 0.0
    return (people_count / frame_area) * 1_000_000


def calculate_speed(prev_positions, curr_positions, fps):
    speeds = []
    for track_id, curr_pos in curr_positions.items():
        if track_id in prev_positions:
            prev_pos = prev_positions[track_id]
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            distance = np.sqrt(dx**2 + dy**2)
            speed = distance * fps
            speeds.append(speed)
    if speeds:
        return np.mean(speeds)
    return 0.0


def calculate_flow_direction(prev_positions, curr_positions):
    """Returns dominant crowd flow direction as (angle, label, individual_angles_list)."""
    angles = []
    for track_id, curr_pos in curr_positions.items():
        if track_id in prev_positions:
            prev_pos = prev_positions[track_id]
            dx = curr_pos[0] - prev_pos[0]
            dy = curr_pos[1] - prev_pos[1]
            if abs(dx) > 1 or abs(dy) > 1:
                angle = np.degrees(np.arctan2(-dy, dx)) % 360
                angles.append(angle)
    if not angles:
        return 0.0, "Stationary", []
    avg_angle = np.mean(angles)
    directions = ["→ East", "↗ NE", "↑ North", "↖ NW",
                   "← West", "↙ SW", "↓ South", "↘ SE"]
    idx = int((avg_angle + 22.5) / 45) % 8
    return round(avg_angle, 1), directions[idx], angles


def get_zone_densities(curr_positions, frame_width, frame_height, grid=(2, 2)):
    cols, rows = grid
    zone_counts = {}
    for r in range(rows):
        for c in range(cols):
            label = f"{chr(65 + r)}{c + 1}"
            zone_counts[label] = 0
    for track_id, (cx, cy) in curr_positions.items():
        col_idx = min(int(cx / (frame_width / cols)), cols - 1)
        row_idx = min(int(cy / (frame_height / rows)), rows - 1)
        label = f"{chr(65 + row_idx)}{col_idx + 1}"
        zone_counts[label] += 1
    return zone_counts


def draw_zones(frame, zone_counts, grid=(2, 2)):
    h, w = frame.shape[:2]
    cols, rows = grid
    for r in range(rows):
        for c in range(cols):
            label = f"{chr(65 + r)}{c + 1}"
            count = zone_counts.get(label, 0)
            x1 = int(c * w / cols)
            y1 = int(r * h / rows)
            x2 = int((c + 1) * w / cols)
            y2 = int((r + 1) * h / rows)
            if count >= 4:
                color = (0, 0, 200)
            elif count >= 2:
                color = (0, 140, 255)
            else:
                color = (0, 180, 0)
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
            cv2.putText(
                frame, f"{label}: {count}p",
                (x1 + 8, y1 + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
            )
    return frame


def save_snapshot(density, avg_speed, trend, zone_counts, flow_dir):
    feature_store.append({
        "timestamp": time.time(),
        "density": round(density, 2),
        "speed": round(avg_speed, 2),
        "trend": round(trend, 3),
        "zones": zone_counts,
        "flow_direction": flow_dir,
    })
    print(f"  [Snapshot] Saved. Total in store: {len(feature_store)}")


RISK_COLORS = {
    "Low":    (0, 255, 0),
    "Medium": (0, 200, 255),
    "High":   (0, 0, 255),
}


def send_to_api(density, speed, trend, acceleration, zone_counts,
                flow_direction, individual_angles=None,
                prev_dominant_angle=None, people_count=0):
    try:
        response = requests.post(
            API_URL,
            json={
                "density":        density,
                "speed":          speed,
                "trend":          trend,
                "acceleration":   acceleration,
                "zones":          zone_counts,
                "flow_direction": flow_direction,
                "individual_angles": individual_angles or [],
                "prev_dominant_angle": prev_dominant_angle,
                "people_count": people_count,
            },
            timeout=1,
        )
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return None


def run_analytics(source):
    global last_snapshot_time

    model = YOLO("yolov8n.pt")

    tracker = DeepSort(
        max_age=30,
        n_init=3,
        max_iou_distance=0.7,
    )

    if source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    frame_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_video    = cap.get(cv2.CAP_PROP_FPS) or 30.0

    api_connected = False
    try:
        r = requests.get("http://localhost:8000/health", timeout=2)
        if r.status_code == 200:
            api_connected = True
    except requests.exceptions.RequestException:
        pass

    print("=" * 65)
    print("  URBAN PULSE AI - Live Analytics + Prediction + Zones")
    print("=" * 65)
    print(f"  Source      : {source}")
    print(f"  Resolution  : {frame_width} x {frame_height}")
    print(f"  Total Frames: {total_frames}")
    print(f"  Video FPS   : {fps_video:.1f}")
    print(f"  API Status  : {'CONNECTED' if api_connected else 'NOT RUNNING'}")
    print(f"  Zones       : 2x2 grid (A1, A2, B1, B2)")
    print("=" * 65)
    print("  Press 'Q' or 'ESC' to quit")
    print("=" * 65)

    frame_count      = 0
    prev_positions   = {}
    all_track_ids    = set()
    last_prediction  = None
    api_call_interval = 10
    density_history  = []
    zone_counts      = {}
    flow_direction   = "Stationary"
    prev_dominant_angle = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("\n[INFO] Video ended.")
            break

        frame_count += 1
        start_time = time.time()

        results = model(frame, classes=[0], verbose=False)

        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                w = x2 - x1
                h = y2 - y1
                detections.append(([x1, y1, w, h], confidence, "person"))

        tracks = tracker.update_tracks(detections, frame=frame)

        people_count   = 0
        curr_positions = {}

        for track in tracks:
            if not track.is_confirmed():
                continue
            people_count += 1
            track_id = track.track_id
            all_track_ids.add(track_id)

            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            curr_positions[track_id] = (cx, cy)

            color = get_color(int(track_id) if str(track_id).isdigit() else hash(track_id) % 1000)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame, f"ID:{track_id}", (x1, y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )
            cv2.circle(frame, (cx, cy), 4, color, -1)

        density   = calculate_density(people_count, frame_width, frame_height)
        avg_speed = calculate_speed(prev_positions, curr_positions, fps_video)
        flow_angle, flow_direction, individual_angles = calculate_flow_direction(prev_positions, curr_positions)
        prev_positions = curr_positions.copy()

        density_history.append(density)
        if len(density_history) > 10:
            density_history.pop(0)

        trend        = density_history[-1] - density_history[0] if len(density_history) >= 2 else 0.0
        acceleration = trend / len(density_history)               if len(density_history) >= 2 else 0.0

        zone_counts = get_zone_densities(curr_positions, frame_width, frame_height, grid=(2, 2))
        frame = draw_zones(frame, zone_counts, grid=(2, 2))

        if time.time() - last_snapshot_time >= SNAPSHOT_INTERVAL:
            save_snapshot(density, avg_speed, trend, zone_counts, flow_direction)
            last_snapshot_time = time.time()

        if api_connected and frame_count % api_call_interval == 0:
            prediction = send_to_api(
                density, avg_speed, trend, acceleration,
                zone_counts, flow_direction,
                individual_angles, prev_dominant_angle, people_count,
            )
            if prediction:
                last_prediction = prediction
            prev_dominant_angle = flow_angle

        elapsed        = time.time() - start_time
        processing_fps = 1.0 / elapsed if elapsed > 0 else 0

        panel_height = 260 if last_prediction else 190
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (400, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        hottest_zone  = max(zone_counts, key=zone_counts.get) if zone_counts else "N/A"
        hottest_count = zone_counts.get(hottest_zone, 0)

        panel_data = [
            ("URBAN PULSE AI", (0, 255, 255)),
            (f"People: {people_count}  |  Unique: {len(all_track_ids)}", (255, 255, 255)),
            (f"Density: {density:.1f} ppl/Mpx", (0, 255, 200)),
            (f"Speed: {avg_speed:.1f} px/s  |  Flow: {flow_direction}", (0, 200, 255)),
            (f"Trend: {trend:+.2f}  |  Accel: {acceleration:+.3f}", (255, 200, 100)),
            (f"Hot Zone: {hottest_zone} ({hottest_count}p)", (255, 100, 100)),
            (f"FPS: {processing_fps:.1f}  |  Frame: {frame_count}", (180, 180, 180)),
        ]

        if last_prediction:
            risk       = last_prediction["risk_level"]
            conf       = last_prediction["confidence"]
            risk_color = RISK_COLORS.get(risk, (255, 255, 255))
            panel_data.append(("---", (80, 80, 80)))
            panel_data.append((f"RISK: {risk} ({conf:.0%})", risk_color))
            panel_data.append((last_prediction["reason"][:50], (200, 200, 200)))

        for i, (text, color) in enumerate(panel_data):
            y_pos = 25 + (i * 24)
            if text == "---":
                cv2.line(frame, (10, y_pos - 5), (390, y_pos - 5), (80, 80, 80), 1)
                continue
            cv2.putText(
                frame, text, (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2 if i == 0 else 1
            )

        if last_prediction:
            risk         = last_prediction["risk_level"]
            border_color = RISK_COLORS.get(risk, (255, 255, 255))
            cv2.rectangle(frame, (0, 0), (frame_width - 1, frame_height - 1), border_color, 3)

        cv2.imshow("Urban Pulse AI - Live", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            print("\n[INFO] User quit.")
            break

        if frame_count % 30 == 0:
            risk_str = last_prediction["risk_level"] if last_prediction else "N/A"
            hot_str = f"{hottest_zone}:{hottest_count}p" if zone_counts else "N/A"
            print(
                f"  Frame {frame_count:>5} | "
                f"People: {people_count:>3} | "
                f"Density: {density:>6.1f} | "
                f"Speed: {avg_speed:>7.1f} px/s | "
                f"Flow: {flow_direction:<12} | "
                f"Hot: {hot_str:<6} | "
                f"Risk: {risk_str:>6} | "
                f"FPS: {processing_fps:.1f}"
            )

    cap.release()
    cv2.destroyAllWindows()

    print()
    print("=" * 65)
    print("  FINAL SUMMARY")
    print("=" * 65)
    print(f"  Frames Processed : {frame_count}")
    print(f"  Unique People    : {len(all_track_ids)}")
    print(f"  Snapshots Saved  : {len(feature_store)}")
    if last_prediction:
        print(f"  Last Risk Level  : {last_prediction['risk_level']}")
        print(f"  Last Confidence  : {last_prediction['confidence']:.0%}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Urban Pulse AI - Live Analytics")
    parser.add_argument(
        "--source",
        type=str,
        default="data/video.mp4",
        help="Path to video file or webcam index (default: data/video.mp4)",
    )
    args = parser.parse_args()

    run_analytics(args.source)