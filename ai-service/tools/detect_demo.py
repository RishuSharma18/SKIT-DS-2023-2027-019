"""Detection + tracking demo. No OCR, no backend, no database needed.

Run from the ai-service folder:
    python tools/detect_demo.py --source samples/parking.mp4
    python tools/detect_demo.py --source samples/parking.mp4 --save samples/out.mp4 --no-show

Keys in the window:  q = quit   SPACE = pause / resume

What to look for:
  * every vehicle gets a box and a stable #ID (ID should not keep changing)
  * the label shows  #id  category  area%  (area% is the box size vs the frame)
  * at the end it prints a summary + a suggested SUV_AREA_RATIO for your video
"""
import argparse
import os
import sys
import time
from collections import defaultdict
from statistics import median

import cv2

# allow "python tools/detect_demo.py" from the ai-service folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import config  # noqa: E402
from app.vehicle import CLASS_NAMES, area_ratio, categorize  # noqa: E402

COLORS = {"bike": (0, 200, 255), "car": (255, 160, 0), "suv": (0, 0, 255)}
MAX_SHOW_WIDTH = 1280


def parse_args():
    ap = argparse.ArgumentParser(description="YOLOv8 vehicle detection + tracking demo")
    ap.add_argument("--source", default=str(config.VIDEO_SOURCE),
                    help="video path, webcam index (0) or rtsp url")
    ap.add_argument("--model", default=config.YOLO_MODEL, help="yolov8n.pt / yolov8s.pt / yolov8m.pt")
    ap.add_argument("--conf", type=float, default=config.CONFIDENCE, help="min detection confidence")
    ap.add_argument("--save", help="write annotated video to this path (e.g. samples/out.mp4)")
    ap.add_argument("--no-show", action="store_true", help="do not open a window")
    ap.add_argument("--max-frames", type=int, default=0, help="stop after N frames (0 = whole video)")
    return ap.parse_args()


def main():
    args = parse_args()
    source = int(args.source) if args.source.isdigit() else args.source
    if isinstance(source, str) and not source.startswith(("rtsp://", "http://", "https://")):
        if not os.path.exists(source):
            sys.exit(f"[ERROR] Video not found: {source}\n"
                     f"        Put your video at ai-service/samples/parking.mp4 or pass --source <path>")

    from ultralytics import YOLO  # imported late so --help works without torch
    model = YOLO(args.model)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        sys.exit("[ERROR] OpenCV could not open the video (bad path or unsupported codec).")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] video {width}x{height} @ {src_fps:.1f} fps | model={args.model} conf={args.conf} "
          f"| SUV_AREA_RATIO={config.SUV_AREA_RATIO}")

    writer = None
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), src_fps, (width, height))

    tracks = defaultdict(lambda: {"cls": 2, "ratios": []})   # track id -> info
    frame_area = width * height
    frames = 0
    t0 = time.time()
    paused = False

    while True:
        if not paused:
            ok, frame = cap.read()
            if not ok:
                break
            frames += 1

            res = model.track(frame, persist=True, classes=config.VEHICLE_CLASSES,
                              tracker="bytetrack.yaml", conf=args.conf, verbose=False)[0]

            counts = defaultdict(int)
            if res.boxes is not None and res.boxes.id is not None:
                boxes = res.boxes.xyxy.cpu().numpy()
                ids = res.boxes.id.int().cpu().tolist()
                clss = res.boxes.cls.int().cpu().tolist()
                for box, tid, cls_id in zip(boxes, ids, clss):
                    ratio = area_ratio(box, frame_area)
                    tracks[tid]["cls"] = cls_id
                    tracks[tid]["ratios"].append(ratio)
                    cat = categorize(cls_id, box, frame_area)
                    counts[cat] += 1

                    x1, y1, x2, y2 = map(int, box)
                    color = COLORS[cat]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"#{tid} {cat} ({CLASS_NAMES.get(cls_id, '?')}) {ratio * 100:.1f}%"
                    cv2.putText(frame, label, (x1, max(15, y1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            fps = frames / max(time.time() - t0, 1e-6)
            hud = (f"frame {frames} | {fps:.1f} fps | bike {counts['bike']}  car {counts['car']}  "
                   f"suv {counts['suv']} | unique IDs {len(tracks)}")
            cv2.rectangle(frame, (0, 0), (width, 26), (0, 0, 0), -1)
            cv2.putText(frame, hud, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

            if writer:
                writer.write(frame)
            if args.max_frames and frames >= args.max_frames:
                break

        if not args.no_show:
            show = frame
            if width > MAX_SHOW_WIDTH:
                s = MAX_SHOW_WIDTH / width
                show = cv2.resize(frame, None, fx=s, fy=s)
            cv2.imshow("Detection demo (q = quit, SPACE = pause)", show)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                paused = not paused

    cap.release()
    if writer:
        writer.release()
        print(f"[INFO] annotated video saved: {args.save}")
    cv2.destroyAllWindows()
    summarize(tracks, frames, time.time() - t0)


def summarize(tracks, frames, seconds):
    print("\n========== SUMMARY ==========")
    print(f"frames processed : {frames}  ({frames / max(seconds, 1e-6):.1f} fps average)")
    print(f"unique vehicles  : {len(tracks)}  (tracker IDs; if far more than real vehicles, IDs are flickering)")
    by_cls = defaultdict(int)
    for t in tracks.values():
        by_cls[CLASS_NAMES.get(t["cls"], "?")] += 1
    for name, n in sorted(by_cls.items()):
        print(f"  {name:<11}: {n}")

    car_med = sorted(median(t["ratios"]) for t in tracks.values() if t["cls"] == 2 and t["ratios"])
    if len(car_med) >= 2:
        print("\nBox size of 'car' tracks (median area % of frame, smallest to largest):")
        print("  " + "  ".join(f"{r * 100:.1f}" for r in car_med))
        print(f"Current SUV_AREA_RATIO = {config.SUV_AREA_RATIO} ({config.SUV_AREA_RATIO * 100:.1f}%)")
        gaps = [(right - left, left, right) for left, right in zip(car_med, car_med[1:])]
        gap, left, right = max(gaps)
        suggestion = (left + right) / 2
        print(f"Largest gap: {left * 100:.1f}% to {right * 100:.1f}% "
              f"(suggested SUV_AREA_RATIO={suggestion:.4f}).")
        print("If that gap separates cars from SUVs in the video, set SUV_AREA_RATIO to the suggestion")
        print("in ai-service/.env; otherwise keep the current value and inspect the detections.")
        print("Note: cars close to the camera look bigger than the same car far away, so use a camera")
        print("angle where parking slots are at a similar distance, or tune the value for that area.")
    elif car_med:
        print("\nNeed at least two distinct car tracks to suggest an SUV_AREA_RATIO.")
    print("To tune detection sensitivity, rerun with --conf <value> (for example --conf 0.3),")
    print("then set CONFIDENCE in ai-service/.env after checking for missed vehicles and false boxes.")
    print("=============================")


if __name__ == "__main__":
    main()
