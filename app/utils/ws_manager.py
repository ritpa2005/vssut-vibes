"""
utils/ws_manager.py

Manages all active WebSocket connections, grouped by room_id.
Handles broadcast, targeted messages, and connection lifecycle.
"""

from fastapi import WebSocket
from typing import Dict, List
import json
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        # room_id -> list of (websocket, user_id, user_name) tuples
        self.rooms: Dict[str, List[dict]] = {}

    # ─── Connection lifecycle ────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append({
            "socket": websocket,
            "user_id": user_id,
            "user_name": user_name
        })

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.rooms:
            self.rooms[room_id] = [
                conn for conn in self.rooms[room_id]
                if conn["socket"] != websocket
            ]
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    # ─── Sending helpers ─────────────────────────────────────────────────────

    async def broadcast(self, room_id: str, message: dict, exclude_user_id: str = None):
        """Send a message to every connected client in a room."""
        if room_id not in self.rooms:
            return
        dead = []
        for conn in self.rooms[room_id]:
            if exclude_user_id and conn["user_id"] == exclude_user_id:
                continue
            try:
                await conn["socket"].send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(conn)
        # clean up any broken sockets found during broadcast
        for conn in dead:
            self.rooms[room_id].remove(conn)

    async def send_to_user(self, room_id: str, user_id: str, message: dict):
        """Send a message to one specific user in a room."""
        if room_id not in self.rooms:
            return
        for conn in self.rooms[room_id]:
            if conn["user_id"] == user_id:
                try:
                    await conn["socket"].send_text(json.dumps(message, default=str))
                except Exception:
                    pass

    # ─── Presence helpers ────────────────────────────────────────────────────

    def get_online_users(self, room_id: str) -> List[dict]:
        """Return list of {user_id, user_name} for everyone currently connected."""
        if room_id not in self.rooms:
            return []
        return [
            {"user_id": c["user_id"], "user_name": c["user_name"]}
            for c in self.rooms[room_id]
        ]

    def is_user_online(self, room_id: str, user_id: str) -> bool:
        if room_id not in self.rooms:
            return False
        return any(c["user_id"] == user_id for c in self.rooms[room_id])

    def active_room_count(self) -> int:
        return len(self.rooms)


# Single shared instance — imported by the router
manager = ConnectionManager()
