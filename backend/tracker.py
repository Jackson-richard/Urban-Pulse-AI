import argparse
import time
import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

def get_color(track_id):
    np.random.seed(track_id * 42)
    return tuple(int(c) for c in np.random.randint(100, 255, size=3))


def run_tracker(source):
    """Run YOLO detection + DeepSORT tracking on a video source."""

    model = YOLO("yolov8n.pt")

    tracker = DeepSort(
        max_age=30,         
        n_init=3,            
        max_iou_distance=0.7, 
        embedder=False,
    )

    if source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_video = cap.get(cv2.CAP_PROP_FPS)

    print("=" * 55)
    print("  URBAN PULSE AI - Person Tracking (DeepSORT)")
    print("=" * 55)
    print(f"  Source      : {source}")
    print(f"  Resolution  : {frame_width} x {frame_height}")
    print(f"  Total Frames: {total_frames}")
    print(f"  Video FPS   : {fps_video:.1f}")
    print("=" * 55)
    print("  Press 'Q' or 'ESC' to quit")
    print("=" * 55)

    frame_count = 0
    all_track_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("\n[INFO] Video ended or no more frames.")
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

        people_count = 0

        for track in tracks:
            if not track.is_confirmed():
                continue

            people_count += 1
            track_id = track.track_id
            all_track_ids.add(track_id)

           
            ltrb = track.to_ltrb()  
            x1, y1, x2, y2 = map(int, ltrb)

            color = get_color(int(track_id) if track_id.isdigit() else hash(track_id) % 1000)

           
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw ID label
            label = f"ID:{track_id}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(
                frame,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0] + 4, y1),
                color,
                -1,
            )
            cv2.putText(
                frame, label, (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2
            )

        elapsed = time.time() - start_time
        processing_fps = 1.0 / elapsed if elapsed > 0 else 0

        overlay_texts = [
            f"Active Tracks: {people_count}",
            f"Total Unique IDs: {len(all_track_ids)}",
            f"FPS: {processing_fps:.1f}",
            f"Frame: {frame_count}/{total_frames}",
        ]

        for i, text in enumerate(overlay_texts):
            y_pos = 30 + (i * 28)
            cv2.putText(
                frame, text, (12, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3
            )
            cv2.putText(
                frame, text, (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2
            )

        cv2.imshow("Urban Pulse AI - Tracking", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            print("\n[INFO] User quit.")
            break

        if frame_count % 30 == 0:
            print(
                f"  Frame {frame_count:>5} | "
                f"Active: {people_count:>3} | "
                f"Unique IDs: {len(all_track_ids):>4} | "
                f"FPS: {processing_fps:.1f}"
            )

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[DONE] Processed {frame_count} frames.")
    print(f"[DONE] Total unique people tracked: {len(all_track_ids)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Urban Pulse AI - Person Tracking")
    parser.add_argument(
        "--source",
        type=str,
        default="data/video.mp4",
        help="Path to video file or webcam index (default: data/video.mp4)",
    )
    args = parser.parse_args()

    run_tracker(args.source)
