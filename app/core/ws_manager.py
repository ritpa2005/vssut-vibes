from fastapi import WebSocket
from typing import Dict, List
from datetime import datetime
import json
import asyncio

HEARTBEAT_TIMEOUT = 300
WATCHDOG_INTERVAL = 60


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[dict]] = {}

    # Connection lifecycle
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str):
        await websocket.accept()

        if room_id not in self.rooms:
            self.rooms[room_id] = []

        # Start watchdog before appending so it can reference the conn dict
        conn = {
            "socket":    websocket,
            "user_id":   user_id,
            "user_name": user_name,
            "last_ping": datetime.utcnow(),
            "watchdog":  None,
        }

        # Launch watchdog task — one per connection
        task = asyncio.create_task(
            self._watchdog(websocket, room_id, conn)
        )
        conn["watchdog"] = task

        self.rooms[room_id].append(conn)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id not in self.rooms:
            return

        for conn in self.rooms[room_id]:
            if conn["socket"] == websocket:
                # Cancel the watchdog so it doesn't fire after disconnect
                if conn["watchdog"] and not conn["watchdog"].done():
                    conn["watchdog"].cancel()
                break

        self.rooms[room_id] = [
            conn for conn in self.rooms[room_id]
            if conn["socket"] != websocket
        ]

        if not self.rooms[room_id]:
            del self.rooms[room_id]

    def update_ping(self, websocket: WebSocket, room_id: str):
        """
        Called by the router every time a ping frame arrives.
        Resets the heartbeat timer for this connection.
        """
        if room_id not in self.rooms:
            return

        for conn in self.rooms[room_id]:
            if conn["socket"] == websocket:
                conn["last_ping"] = datetime.utcnow()
                break

    # Watchdog
    async def _watchdog(
        self,
        websocket: WebSocket,
        room_id:   str,
        conn:      dict
    ):
        """
        Runs in the background for each connection.
        Every WATCHDOG_INTERVAL seconds it checks when the last ping was.
        If more than HEARTBEAT_TIMEOUT seconds have passed with no ping,
        the connection is closed with code 4008 (timeout).

        Frontend should send a ping every 30s.
        Timeout is 5 min — generous enough to survive brief network drops.
        """
        try:
            while True:
                await asyncio.sleep(WATCHDOG_INTERVAL)

                silence = (datetime.utcnow() - conn["last_ping"]).total_seconds()

                if silence >= HEARTBEAT_TIMEOUT:
                    # Notify the client before closing
                    try:
                        await websocket.send_text(json.dumps({
                            "type":   "error",
                            "detail": "Connection closed due to inactivity (5 minutes)."
                        }))
                    except Exception:
                        pass   # socket may already be dead

                    # Close and clean up
                    try:
                        await websocket.close(code=4008, reason="Heartbeat timeout")
                    except Exception:
                        pass

                    self.disconnect(websocket, room_id)

                    # Notify remaining room members this user went offline
                    await self.broadcast(room_id, {
                        "type":      "leave",
                        "user_id":   conn["user_id"],
                        "user_name": conn["user_name"],
                    })
                    return   # watchdog task ends

        except asyncio.CancelledError:
            # Normal path — disconnect() cancelled this task cleanly
            pass


    async def broadcast(
        self,
        room_id:         str,
        message:         dict,
        exclude_user_id: str = None
    ):
        """Send to all connected clients in a room in parallel."""
        if room_id not in self.rooms:
            return

        payload = json.dumps(message, default=str)
        targets = [
            conn for conn in self.rooms[room_id]
            if conn["user_id"] != exclude_user_id
        ]

        # Parallel broadcast — all sends happen simultaneously
        results = await asyncio.gather(
            *[conn["socket"].send_text(payload) for conn in targets],
            return_exceptions=True
        )

        # Clean up any sockets that errored during broadcast
        dead = [
            targets[i]["socket"]
            for i, result in enumerate(results)
            if isinstance(result, Exception)
        ]
        for dead_socket in dead:
            self.disconnect(dead_socket, room_id)

    async def send_to_user(self, room_id: str, user_id: str, message: dict):
        """Send to one specific user in a room."""
        if room_id not in self.rooms:
            return

        payload = json.dumps(message, default=str)
        for conn in self.rooms[room_id]:
            if conn["user_id"] == user_id:
                try:
                    await conn["socket"].send_text(payload)
                except Exception:
                    self.disconnect(conn["socket"], room_id)
                break

    # Presence
    def get_online_users(self, room_id: str) -> List[dict]:
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


# Single shared instance imported by the router
manager = ConnectionManager()