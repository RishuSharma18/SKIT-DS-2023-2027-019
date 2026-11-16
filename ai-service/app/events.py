import requests
from . import config

_replay_warning_shown = False


def send(event_type: str, **payload):
    """POST one event to the backend. Never crash the video loop on network errors."""
    global _replay_warning_shown
    if config.SOURCE_MODE == "video" and event_type != "occupancy":
        if not _replay_warning_shown:
            print("[events] prerecorded-video session/history writes are disabled")
            _replay_warning_shown = True
        return None

    body = {"type": event_type, "cameraId": config.CAMERA_ID, **payload}
    try:
        r = requests.post(
            f"{config.BACKEND_URL}/api/events",
            json=body,
            headers={"x-api-key": config.API_KEY},
            timeout=3,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"[events] failed to send {event_type}: {e}")
        return None
