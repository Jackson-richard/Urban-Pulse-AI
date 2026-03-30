"""
Urban Pulse AI - Step 1: YOLO Person Detection
================================================
Detects people in a video file using YOLOv8 (pretrained).
Draws bounding boxes around detected people.
Shows people count and FPS on each frame.

Usage:
    python backend/detect.py
    python backend/detect.py --source path/to/video.mp4
    python backend/detect.py --source 0          # webcam
"""

import argparse
import time
import cv2
from ultralytics import YOLO


def run_detection(source):
    """Run YOLO person detection on a video source."""

    # Load pretrained YOLOv8 nano model (auto-downloads on first run)
    model = YOLO("yolov8n.pt")

    # Open video source (file path or webcam index)
    if source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        print("Make sure the file exists or webcam is connected.")
        return

    # Get video info
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_video = cap.get(cv2.CAP_PROP_FPS)

    print("=" * 50)
    print("  URBAN PULSE AI - Person Detection")
    print("=" * 50)
    print(f"  Source      : {source}")
    print(f"  Resolution  : {frame_width} x {frame_height}")
    print(f"  Total Frames: {total_frames}")
    print(f"  Video FPS   : {fps_video:.1f}")
    print("=" * 50)
    print("  Press 'Q' or 'ESC' to quit")
    print("=" * 50)

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("\n[INFO] Video ended or no more frames.")
            break

        frame_count += 1
        start_time = time.time()

        # Run YOLO detection
        # classes=[0] filters for 'person' class only (class 0 in COCO dataset)
        results = model(frame, classes=[0], verbose=False)

        # Count people and draw bounding boxes
        people_count = 0

        for result in results:
            for box in result.boxes:
                # Get bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])

                people_count += 1

                # Draw bounding box (green)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Draw confidence label
                label = f"Person {confidence:.0%}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(
                    frame,
                    (x1, y1 - label_size[1] - 10),
                    (x1 + label_size[0], y1),
                    (0, 255, 0),
                    -1,
                )
                cv2.putText(
                    frame, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1
                )

        # Calculate processing FPS
        elapsed = time.time() - start_time
        processing_fps = 1.0 / elapsed if elapsed > 0 else 0

        # Draw info overlay (top-left)
        overlay_texts = [
            f"People Count: {people_count}",
            f"FPS: {processing_fps:.1f}",
            f"Frame: {frame_count}/{total_frames}",
        ]

        for i, text in enumerate(overlay_texts):
            y_pos = 30 + (i * 30)
            # Dark background for readability
            cv2.putText(
                frame, text, (12, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3
            )
            # Green text on top
            cv2.putText(
                frame, text, (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )

        # Show frame
        cv2.imshow("Urban Pulse AI - Detection", frame)

        # Quit on 'q' or ESC
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            print("\n[INFO] User quit.")
            break

        # Print to console every 30 frames
        if frame_count % 30 == 0:
            print(f"  Frame {frame_count:>5} | People: {people_count:>3} | FPS: {processing_fps:.1f}")

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[DONE] Processed {frame_count} frames total.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Urban Pulse AI - Person Detection")
    parser.add_argument(
        "--source",
        type=str,
        default="data/video.mp4",
        help="Path to video file or webcam index (default: data/video.mp4)",
    )
    args = parser.parse_args()

    run_detection(args.source)