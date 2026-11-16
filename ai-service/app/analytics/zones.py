"""Backend-sourced slot polygons, tripwires, and parking-rule evaluation."""
from time import time

import cv2
import numpy as np


class ZoneMap:
    def __init__(self, data):
        self.camera_id = data["camera_id"]
        self.slots = [
            {**slot, "polygon_array": np.asarray(slot["polygon"], dtype=np.int32)}
            for slot in data.get("slots", [])
            if len(slot.get("polygon", [])) >= 3
        ]
        self.no_parking_zones = [
            {**zone, "polygon_array": np.asarray(zone["polygon"], dtype=np.int32)}
            for zone in data.get("no_parking_zones", [])
            if len(zone.get("polygon", [])) >= 3
        ]
        self.tripwires = data.get("tripwires", [])

    def containing_slots(self, box, category=None):
        x1, y1, x2, y2 = map(float, box)
        anchor = ((x1 + x2) / 2, y2)
        matches = []
        for slot in self.slots:
            if category and not self._fits(slot.get("vehicle_category"), category):
                continue
            polygon = slot["polygon_array"]
            if cv2.pointPolygonTest(polygon, anchor, False) >= 0:
                matches.append(slot)
        return matches

    def straddled_slots(self, box):
        x1, y1, x2, y2 = map(float, box)
        box_area = max(1.0, (x2 - x1) * (y2 - y1))
        rectangle = np.asarray([
            [x1, y1], [x2, y1], [x2, y2], [x1, y2],
        ], dtype=np.float32)
        matches = []
        for slot in self.slots:
            polygon = slot["polygon_array"].astype(np.float32)
            overlap_area, _ = cv2.intersectConvexConvex(rectangle, polygon)
            if overlap_area / box_area >= 0.18:
                matches.append(slot)
        return matches

    def in_no_parking_zone(self, point):
        return any(
            cv2.pointPolygonTest(zone["polygon_array"], tuple(map(float, point)), False) >= 0
            for zone in self.no_parking_zones
        )

    @staticmethod
    def _fits(slot_category, vehicle_category):
        if not slot_category:
            return True
        allowed = {
            "TWO_WHEELER": {"TWO_WHEELER"},
            "COMPACT_CAR": {"COMPACT_CAR"},
            "SUV_SEDAN": {"SUV_SEDAN"},
            "HEAVY_VEHICLE": {"HEAVY_VEHICLE"},
        }
        return vehicle_category in allowed.get(slot_category, {slot_category})


class ZoneEngine:
    def __init__(self, zone_map, wrong_parking_seconds=15, stationary_speed=4.0):
        self.zone_map = zone_map
        self.wrong_parking_seconds = wrong_parking_seconds
        self.stationary_speed = stationary_speed
        self.tracks = {}

    def update(self, observation, timestamp=None):
        now = timestamp if timestamp is not None else time()
        track_id = observation["track_id"]
        box = observation["box"]
        category = observation["category"]
        point = ((box[0] + box[2]) / 2, box[3])
        state = self.tracks.setdefault(track_id, {
            "previous_point": None,
            "previous_time": None,
            "stationary_since": None,
            "reported_violation": False,
            "last_slot": None,
        })
        previous_point = state["previous_point"]
        speed = float("inf")
        if previous_point is not None and state["previous_time"] is not None:
            elapsed = max(0.001, now - state["previous_time"])
            speed = float(np.hypot(point[0] - previous_point[0], point[1] - previous_point[1])) / elapsed
        state["previous_point"] = point
        state["previous_time"] = now

        candidates = self.zone_map.containing_slots(box, category)
        straddled = self.zone_map.straddled_slots(box)
        slot = candidates[0] if candidates and len(straddled) <= 1 else None
        events = []
        slot_id = slot.get("slot_id") if slot else None
        if slot_id != state["last_slot"]:
            if slot_id:
                events.append({"event_type": "ENTRY", "slot_id": slot_id})
            elif state["last_slot"]:
                events.append({"event_type": "EXIT", "slot_id": state["last_slot"]})
            state["last_slot"] = slot_id

        outside_valid_slot = slot is None
        restricted = self.zone_map.in_no_parking_zone(point)
        straddling = len(straddled) > 1
        if outside_valid_slot and speed <= self.stationary_speed:
            if state["stationary_since"] is None:
                state["stationary_since"] = now
            parked_seconds = now - state["stationary_since"]
            if (restricted or straddling or parked_seconds >= self.wrong_parking_seconds) and not state["reported_violation"]:
                reason = "straddling parking spaces" if straddling else (
                    "stopped in a no-parking zone" if restricted else "stationary outside a valid parking space"
                )
                events.append({
                    "event_type": "ALERT",
                    "alert_type": "WRONG_PARKING",
                    "message": f"Track {track_id} {reason}",
                })
                state["reported_violation"] = True
        else:
            state["stationary_since"] = None
            if not restricted and not straddling:
                state["reported_violation"] = False

        return slot, events

    def crossed_tripwires(self, observation, previous_observation=None):
        if previous_observation is None:
            return []
        current_box = observation["box"]
        previous_box = previous_observation["box"]
        previous_point = ((previous_box[0] + previous_box[2]) / 2, previous_box[3])
        current_point = ((current_box[0] + current_box[2]) / 2, current_box[3])
        crossings = []
        for wire in self.zone_map.tripwires:
            (x1, y1), (x2, y2) = wire["line"]
            dx, dy = current_point[0] - previous_point[0], current_point[1] - previous_point[1]
            wire_dx, wire_dy = x2 - x1, y2 - y1
            denominator = dx * wire_dy - dy * wire_dx
            if denominator == 0:
                continue
            offset_x, offset_y = x1 - previous_point[0], y1 - previous_point[1]
            along_track = (offset_x * wire_dy - offset_y * wire_dx) / denominator
            along_wire = (offset_x * dy - offset_y * dx) / denominator
            if 0 <= along_track <= 1 and 0 <= along_wire <= 1:
                crossings.append(wire.get("event_type", "ENTRY"))
        return crossings

    def forget(self, track_id):
        self.tracks.pop(track_id, None)
