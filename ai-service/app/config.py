import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
API_KEY = os.getenv("AI_API_KEY", "dev-key")
CAMERA_ID = os.getenv("CAMERA_ID", "cam-1")

_src = os.getenv("VIDEO_SOURCE", "samples/parking.mp4")
VIDEO_SOURCE = int(_src) if _src.isdigit() else _src

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
SLOTS_FILE = os.getenv("SLOTS_FILE", "config/slots.json")
CONFIDENCE = float(os.getenv("CONFIDENCE", "0.4"))
OCR_EVERY_N_FRAMES = int(os.getenv("OCR_EVERY_N_FRAMES", "10"))
EXIT_AFTER_MISSING_FRAMES = int(os.getenv("EXIT_AFTER_MISSING_FRAMES", "45"))
ENTRY_CONFIRM_FRAMES = int(os.getenv("ENTRY_CONFIRM_FRAMES", "15"))
STATIONARY_SECONDS = float(os.getenv("STATIONARY_SECONDS", "3"))
WRONG_PARK_SECONDS = float(os.getenv("WRONG_PARK_SECONDS", "8"))
SUV_AREA_RATIO = float(os.getenv("SUV_AREA_RATIO", "0.045"))

# COCO class ids used by YOLOv8: 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 3, 5, 7]
