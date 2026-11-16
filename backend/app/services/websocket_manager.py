import json
import logging
from typing import List, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, payload: Any):
        if not self.active_connections:
            return

        message = json.dumps({"event": event_type, "data": payload}, default=str)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as exc:
                logger.warning(f"Failed to send to websocket client: {exc}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_alert(self, alert_dict: dict):
        await self.broadcast("alert:new", alert_dict)

    async def broadcast_slot_update(self, slots_data: list):
        await self.broadcast("slots:update", slots_data)

    async def broadcast_session_update(self, session_dict: dict):
        await self.broadcast("session:update", session_dict)

    async def broadcast_session_new(self, session_dict: dict):
        await self.broadcast("session:new", session_dict)

ws_manager = WebSocketManager()
