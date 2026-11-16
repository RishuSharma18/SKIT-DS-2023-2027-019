import os
import re
import time
import uuid
import base64
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

def save_base64_snapshot(snapshot_data: str) -> str | None:
    if not snapshot_data or not isinstance(snapshot_data, str):
        return None

    trimmed = snapshot_data.strip()
    if not trimmed:
        return None

    if trimmed.startswith("/uploads/") or trimmed.startswith("http://") or trimmed.startswith("https://"):
        return trimmed
    if trimmed.startswith("uploads/"):
        return f"/{trimmed}"

    uploads_dir: Path = settings.UPLOADS_DIR
    uploads_dir.mkdir(parents=True, exist_ok=True)

    extension = "jpg"
    clean_base64 = trimmed

    # Detect data URI format: data:image/xxx;base64,...
    match = re.match(r"^data:image\/([a-zA-Z0-9+]+);base64,(.+)$", trimmed, re.DOTALL)
    if match:
        ext = match.group(1).lower()
        extension = "jpg" if ext in ["jpeg", "jpg"] else ext
        clean_base64 = match.group(2).strip()
    elif ";base64," in trimmed:
        clean_base64 = trimmed.split(";base64,")[1].strip()

    filename = f"snap-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}.{extension}"
    file_path = uploads_dir / filename

    try:
        binary_data = base64.b64decode(clean_base64)
        with open(file_path, "wb") as f:
            f.write(binary_data)
        logger.info(f"Saved snapshot to {file_path}")
        return f"/uploads/{filename}"
    except Exception as exc:
        logger.error(f"Failed to decode and save snapshot: {exc}")
        return None
