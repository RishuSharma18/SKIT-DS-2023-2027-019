"""Loads camera slot polygons and tripwires from the backend API."""
from urllib.parse import quote

import httpx

from .. import config
from ..analytics.zones import ZoneMap


def fetch_zone_map(camera_id):
    endpoint = f"{config.BACKEND_URL.rstrip('/')}/api/v1/cameras/{quote(camera_id, safe='')}/zones"
    try:
        response = httpx.get(
            endpoint,
            headers={"x-api-key": config.API_KEY},
            timeout=5,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        local_file = config.SERVICE_DIR / "config" / "slots.json"
        if local_file.is_file():
            try:
                import json
                raw = json.loads(local_file.read_text(encoding="utf-8"))
                slots = [
                    {
                        "slot_id": s.get("slotId") or s.get("slot_id"),
                        "vehicle_category": {
                            "bike": "TWO_WHEELER",
                            "car": "COMPACT_CAR",
                            "suv": "SUV_SEDAN",
                            "heavy_vehicle": "HEAVY_VEHICLE",
                        }.get(str(s.get("type", "car")).lower(), "COMPACT_CAR"),
                        "polygon": s.get("polygon", []),
                    }
                    for s in raw.get("slots", [])
                ]
                return ZoneMap({
                    "camera_id": camera_id,
                    "slots": slots,
                    "no_parking_zones": [],
                    "tripwires": [],
                })
            except Exception:
                pass
        raise RuntimeError(f"Unable to load zones for camera {camera_id}: {error}") from error
    data = response.json()
    if data.get("camera_id") != camera_id:
        raise RuntimeError(f"Backend returned a zone map for the wrong camera: {data.get('camera_id')}")
    return ZoneMap(data)
