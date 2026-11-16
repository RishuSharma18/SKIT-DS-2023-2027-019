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
        raise RuntimeError(f"Unable to load zones for camera {camera_id}: {error}") from error
    data = response.json()
    if data.get("camera_id") != camera_id:
        raise RuntimeError(f"Backend returned a zone map for the wrong camera: {data.get('camera_id')}")
    return ZoneMap(data)
