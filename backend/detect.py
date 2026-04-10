
import argparse
import time
import cv2
from ultralytics import YOLO


def run_detection(source):
    model = YOLO("yolov8n.pt")
    if source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Could not open video source: {source}")
        print("Make sure the file exists or webcam is connected.")
        return

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
        results = model(frame, classes=[0], verbose=False)
        people_count = 0

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])

                people_count += 1
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
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

        elapsed = time.time() - start_time
        processing_fps = 1.0 / elapsed if elapsed > 0 else 0
        overlay_texts = [
            f"People Count: {people_count}",
            f"FPS: {processing_fps:.1f}",
            f"Frame: {frame_count}/{total_frames}",
        ]

        for i, text in enumerate(overlay_texts):
            y_pos = 30 + (i * 30)
            cv2.putText(
                frame, text, (12, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3
            )
            
            cv2.putText(
                frame, text, (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )

        cv2.imshow("Urban Pulse AI - Detection", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            print("\n[INFO] User quit.")
            break

        if frame_count % 30 == 0:
            print(f"  Frame {frame_count:>5} | People: {people_count:>3} | FPS: {processing_fps:.1f}")

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