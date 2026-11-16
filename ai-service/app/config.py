import os
from pathlib import Path
from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
API_KEY = os.getenv("AI_API_KEY", "dev-key")
CAMERA_ID = os.getenv("CAMERA_ID", "cam-1")

_src = os.getenv("VIDEO_SOURCE", "samples/parking.mp4")
if _src.isdigit():
    VIDEO_SOURCE = int(_src)
elif _src.startswith(("rtsp://", "http://", "https://")):
    VIDEO_SOURCE = _src
else:
    _source_path = Path(_src)
    VIDEO_SOURCE = str((_source_path if _source_path.is_absolute() else SERVICE_DIR / _source_path).resolve())

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "1280"))
TILE_OVERLAP = float(os.getenv("TILE_OVERLAP", "0.10"))
TILE_MIN_WIDTH = int(os.getenv("TILE_MIN_WIDTH", "1920"))
TILE_MIN_HEIGHT = int(os.getenv("TILE_MIN_HEIGHT", "1200"))
TILE_NMS_IOU = float(os.getenv("TILE_NMS_IOU", "0.65"))
SLOTS_FILE = os.getenv("SLOTS_FILE", "config/slots.json")
SLOTS_PATH = Path(SLOTS_FILE)
if not SLOTS_PATH.is_absolute():
    SLOTS_PATH = SERVICE_DIR / SLOTS_PATH
CONFIDENCE = float(os.getenv("CONFIDENCE", "0.25"))
ENABLE_OCR = os.getenv("ENABLE_OCR", "1") == "1"   # set 0 to test detection without EasyOCR
OCR_EVERY_N_FRAMES = int(os.getenv("OCR_EVERY_N_FRAMES", "10"))
EXIT_AFTER_MISSING_FRAMES = int(os.getenv("EXIT_AFTER_MISSING_FRAMES", "45"))
ENTRY_CONFIRM_FRAMES = int(os.getenv("ENTRY_CONFIRM_FRAMES", "15"))
STATIONARY_SECONDS = float(os.getenv("STATIONARY_SECONDS", "3"))
STATIONARY_MIN_MOVEMENT = float(os.getenv("STATIONARY_MIN_MOVEMENT", "5"))
# COCO class IDs: 2=car (including SUVs), 3=motorcycle. COCO cannot identify SUVs separately.
VEHICLE_CLASSES = [2, 3]
SOURCE_MODE = (
    "webcam" if isinstance(VIDEO_SOURCE, int)
    else "network" if VIDEO_SOURCE.startswith(("rtsp://", "http://", "https://"))
    else "video"
)
