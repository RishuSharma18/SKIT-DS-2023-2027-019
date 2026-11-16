import os
import json
from pathlib import Path
from dotenv import load_dotenv

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVICE_DIR / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
API_KEY = os.getenv("AI_API_KEY", "dev-key")
CAMERA_ID = os.getenv("CAMERA_ID", "cam-1")

def parse_source(value):
    if value.isdigit():
        return int(value)
    if value.startswith(("rtsp://", "http://", "https://")):
        return value
    source_path = Path(value)
    return str((source_path if source_path.is_absolute() else SERVICE_DIR / source_path).resolve())


def parse_streams():
    raw_urls = os.getenv("RTSP_URLS", "").strip()
    if raw_urls:
        try:
            parsed = json.loads(raw_urls)
        except json.JSONDecodeError:
            parsed = dict(
                item.split("=", 1)
                for item in raw_urls.split(",")
                if "=" in item
            )
        if not isinstance(parsed, dict) or not parsed:
            raise ValueError("RTSP_URLS must be a JSON object or comma-separated CAMERA_ID=URL pairs")
        if any(not str(camera_id).strip() or not str(url).strip()
               for camera_id, url in parsed.items()):
            raise ValueError("RTSP_URLS camera IDs and source URLs cannot be empty")
        return {str(camera_id): parse_source(str(url)) for camera_id, url in parsed.items()}
    return {CAMERA_ID: parse_source(os.getenv("VIDEO_SOURCE", "samples/parking.mp4"))}


CAMERA_STREAMS = parse_streams()
if CAMERA_ID not in CAMERA_STREAMS:
    CAMERA_ID = next(iter(CAMERA_STREAMS))
VIDEO_SOURCE = CAMERA_STREAMS.get(CAMERA_ID, next(iter(CAMERA_STREAMS.values())))

YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
_yolo_path = Path(YOLO_MODEL)
if not _yolo_path.is_absolute() and (SERVICE_DIR / _yolo_path).is_file():
    YOLO_MODEL = str((SERVICE_DIR / _yolo_path).resolve())

YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "1280"))
TILE_OVERLAP = float(os.getenv("TILE_OVERLAP", "0.10"))
TILE_MIN_WIDTH = int(os.getenv("TILE_MIN_WIDTH", "1920"))
TILE_MIN_HEIGHT = int(os.getenv("TILE_MIN_HEIGHT", "1200"))
TILE_NMS_IOU = float(os.getenv("TILE_NMS_IOU", "0.65"))
CONFIDENCE = float(os.getenv("CONFIDENCE_THRESHOLD", os.getenv("CONFIDENCE", "0.25")))
FRAME_SKIP = max(0, int(os.getenv("FRAME_SKIP", "0")))
TRACKER = os.getenv("TRACKER", "bytetrack.yaml")
PLATE_MODEL = os.getenv("PLATE_MODEL", "").strip() or None
if PLATE_MODEL and not Path(PLATE_MODEL).is_absolute() and (SERVICE_DIR / PLATE_MODEL).is_file():
    PLATE_MODEL = str((SERVICE_DIR / PLATE_MODEL).resolve())

EASYOCR_MODEL_DIR = Path(os.getenv("EASYOCR_MODEL_DIR", str(SERVICE_DIR / "models" / "easyocr")))
if not EASYOCR_MODEL_DIR.is_absolute():
    EASYOCR_MODEL_DIR = SERVICE_DIR / EASYOCR_MODEL_DIR
EASYOCR_MODEL_DIR.mkdir(parents=True, exist_ok=True)
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.60"))
OCR_VOTE_FRAMES = max(1, int(os.getenv("OCR_VOTE_FRAMES", "5")))
WRONG_PARKING_SECONDS = max(1, int(os.getenv("WRONG_PARKING_SECONDS", "15")))
EVENT_SNAPSHOT_DIR = Path(os.getenv("EVENT_SNAPSHOT_DIR", "media/alerts"))
if not EVENT_SNAPSHOT_DIR.is_absolute():
    EVENT_SNAPSHOT_DIR = SERVICE_DIR / EVENT_SNAPSHOT_DIR
ENABLE_OCR = os.getenv("ENABLE_OCR", "1") == "1"   # set 0 to test detection without EasyOCR
OCR_EVERY_N_FRAMES = int(os.getenv("OCR_EVERY_N_FRAMES", "10"))
EXIT_AFTER_MISSING_FRAMES = int(os.getenv("EXIT_AFTER_MISSING_FRAMES", "45"))
ENTRY_CONFIRM_FRAMES = int(os.getenv("ENTRY_CONFIRM_FRAMES", "15"))
STATIONARY_SECONDS = float(os.getenv("STATIONARY_SECONDS", "3"))
STATIONARY_MIN_MOVEMENT = float(os.getenv("STATIONARY_MIN_MOVEMENT", "5"))
# Map custom model class IDs/names to canonical values such as {"0":"SUV_SEDAN"}.
CUSTOM_CLASS_MAP = {}
if os.getenv("CUSTOM_CLASS_MAP", "").strip():
    CUSTOM_CLASS_MAP = json.loads(os.environ["CUSTOM_CLASS_MAP"])
VEHICLE_CLASSES = [2, 3, 5, 7]


def source_mode(source):
    if isinstance(source, int):
        return "webcam"
    if str(source).startswith(("rtsp://", "http://", "https://")):
        return "network"
    return "video"


SOURCE_MODE = source_mode(VIDEO_SOURCE)
