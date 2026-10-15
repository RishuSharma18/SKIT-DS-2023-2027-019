"""Draw parking-slot polygons on a video frame and save them to config/slots.json.

Run from the ai-service folder:
    python tools/draw_slots.py --source samples/parking.mp4
    python tools/draw_slots.py --source samples/parking.mp4 --frame 120 --zone A
    python tools/draw_slots.py --source samples/parking.mp4 --append     (keep slots already saved)

Mouse : LEFT click  = add a corner of the current slot (click 4 corners around the parking box)
        RIGHT click = undo the last corner
Keys  : ENTER (or n) = finish the current slot       1 / 2 / 3 = slot type: bike / car / suv
        d = delete the last finished slot             s = save slots.json          q = quit

Slot IDs are automatic: A-01, A-02, ... in the order you finish them.
"""
import argparse
import json
import os
import shutil
import sys

import cv2
import numpy as np

TYPES = {ord("1"): "bike", ord("2"): "car", ord("3"): "suv"}
TYPE_COLORS = {"bike": (0, 200, 255), "car": (0, 200, 0), "suv": (255, 120, 0)}
MAX_SHOW_WIDTH = 1280


class SlotEditor:
    """Holds the drawing state. Kept separate from the GUI so it is easy to test."""

    def __init__(self, zone="A", slots=None):
        self.zone = zone
        self.slots = slots or []          # [{slotId, type, polygon}]
        self.points = []                  # corners of the slot being drawn (original pixel coords)
        self.slot_type = "car"

    @property
    def next_id(self):
        prefix = f"{self.zone}-"
        numbers = [
            int(slot_id[len(prefix):])
            for slot in self.slots
            if (slot_id := str(slot.get("slotId", ""))).startswith(prefix)
            and slot_id[len(prefix):].isdigit()
        ]
        return f"{self.zone}-{max(numbers, default=0) + 1:02d}"

    def add_point(self, x, y):
        self.points.append([int(x), int(y)])

    def undo_point(self):
        if self.points:
            self.points.pop()

    def finish_slot(self):
        if len(self.points) < 3:
            return False
        self.slots.append({"slotId": self.next_id, "type": self.slot_type, "polygon": self.points})
        self.points = []
        return True

    def delete_last_slot(self):
        if self.slots:
            self.slots.pop()

    def counts(self):
        out = {"bike": 0, "car": 0, "suv": 0}
        for s in self.slots:
            out[s["type"]] += 1
        return out


def save_slots(slots, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")          # never lose the previous version
    with open(path, "w") as f:
        json.dump({"slots": slots}, f, indent=2)


def load_frame(source, frame_no):
    if source.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        img = cv2.imread(source)
        if img is None:
            sys.exit(f"[ERROR] Could not read image: {source}")
        return img
    if not os.path.exists(source):
        sys.exit(f"[ERROR] Video not found: {source}")
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        sys.exit("[ERROR] Could not read that frame. Try a smaller --frame number.")
    return frame


def render(base, ed, scale):
    img = base.copy()

    def sc(pt):
        return int(pt[0] * scale), int(pt[1] * scale)

    for s in ed.slots:
        pts = np.array([sc(p) for p in s["polygon"]], dtype=np.int32)
        color = TYPE_COLORS[s["type"]]
        overlay = img.copy()
        cv2.fillPoly(overlay, [pts], color)
        img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)
        cv2.polylines(img, [pts], True, color, 2)
        cv2.putText(img, f"{s['slotId']} {s['type']}", (pts[0][0], pts[0][1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    if ed.points:
        pts = [sc(p) for p in ed.points]
        for p in pts:
            cv2.circle(img, p, 4, (0, 255, 255), -1)
        if len(pts) > 1:
            cv2.polylines(img, [np.array(pts, dtype=np.int32)], False, (0, 255, 255), 2)

    c = ed.counts()
    lines = [
        f"Drawing: {ed.next_id}  type: {ed.slot_type.upper()}   (1=bike 2=car 3=suv)",
        f"Saved slots: {len(ed.slots)}  (bike {c['bike']}, car {c['car']}, suv {c['suv']})",
        "Click corners | ENTER finish slot | right-click undo | d delete last | s save | q quit",
    ]
    cv2.rectangle(img, (0, 0), (img.shape[1], 70), (0, 0, 0), -1)
    for i, t in enumerate(lines):
        cv2.putText(img, t, (8, 20 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
    return img


def main():
    ap = argparse.ArgumentParser(description="Draw parking slot polygons")
    ap.add_argument("--source", default="samples/parking.mp4", help="video or image file")
    ap.add_argument("--frame", type=int, default=30, help="which video frame to draw on")
    ap.add_argument("--out", default="config/slots.json", help="where to save the slots")
    ap.add_argument("--zone", default="A", help="slot ID prefix, e.g. A -> A-01, A-02 ...")
    ap.add_argument("--append", action="store_true", help="start from the slots already in --out")
    args = ap.parse_args()

    frame = load_frame(args.source, args.frame)
    h, w = frame.shape[:2]
    scale = min(1.0, MAX_SHOW_WIDTH / w)
    print(f"[INFO] frame {w}x{h}, window scale {scale:.2f} (saved coordinates are in real video pixels)")

    existing = []
    if args.append and os.path.exists(args.out):
        existing = json.load(open(args.out)).get("slots", [])
        print(f"[INFO] loaded {len(existing)} existing slots")
    ed = SlotEditor(zone=args.zone, slots=existing)

    win = "Draw parking slots"
    cv2.namedWindow(win)
    base = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1.0 else frame

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            ed.add_point(x / scale, y / scale)
        elif event == cv2.EVENT_RBUTTONDOWN:
            ed.undo_point()

    cv2.setMouseCallback(win, on_mouse)
    saved_once = False

    while True:
        cv2.imshow(win, render(base, ed, scale))
        key = cv2.waitKey(30) & 0xFF
        if key in (13, ord("n")):
            if not ed.finish_slot():
                print("[WARN] need at least 3 corners before finishing a slot")
        elif key in TYPES:
            ed.slot_type = TYPES[key]
        elif key == ord("d"):
            ed.delete_last_slot()
        elif key == ord("s"):
            save_slots(ed.slots, args.out)
            saved_once = True
            c = ed.counts()
            print(f"[SAVED] {len(ed.slots)} slots -> {args.out}  (bike {c['bike']}, car {c['car']}, suv {c['suv']})")
        elif key == ord("q"):
            break

    cv2.destroyAllWindows()
    if ed.slots and not saved_once:
        print("[WARN] you quit without saving (press s before q next time)")
    elif ed.slots:
        print("\nNext: make the database match these slots:")
        print("  cd ../backend && node src/scripts/seedFromSlots.js")


if __name__ == "__main__":
    main()
