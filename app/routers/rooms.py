"""
routers/rooms.py

HTTP routes for room management + WebSocket endpoint for real-time messaging.

WebSocket message protocol (JSON):
  Client → Server:
    { "type": "message", "content": "Hello!", "attachment": null }
    { "type": "ping" }

  Server → Client:
    { "type": "message",    ...MessageResponse fields... }
    { "type": "join",       "user_id": "...", "user_name": "..." }
    { "type": "leave",      "user_id": "...", "user_name": "..." }
    { "type": "kick",       "user_id": "...", "user_name": "..." }
    { "type": "room_closed" }
    { "type": "error",      "detail": "..." }
    { "type": "pong" }
    { "type": "presence",   "online_users": [...] }
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from typing import List, Optional
import json

from app.models import RoomCreate, RoomUpdate, RoomResponse, RoomPreviewResponse, MessageResponse
from app.services.room_service import (
    create_room, get_room_by_id, get_room_by_invite_code,
    get_user_rooms, update_room, close_room,
    join_room, kick_member, leave_room,
    save_message, get_messages, mark_messages_read,
    room_to_response, message_to_response
)
from app.utils.dependencies import get_current_active_user
from app.utils.ws_manager import manager
from app.utils.security import decode_token
from app.database import get_users_collection
from bson import ObjectId

router = APIRouter(prefix="/rooms", tags=["Collaboration Rooms"])


# ─── Auth helper for WebSocket ────────────────────────────────────────────────
# HTTP routes use Depends(get_current_active_user).
# WebSockets can't send Authorization headers, so the token
# is passed as a query param and validated manually here.

async def get_ws_user(token: str) -> dict:
    """Decode JWT and return user dict for WebSocket connections."""
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    users_col = await get_users_collection()
    user = await users_col.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
    return user


# ─── Room Management (HTTP) ───────────────────────────────────────────────────

@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room_route(
    room_data: RoomCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Mentor creates a new collaboration room.
    Returns the room with a unique shareable invite link.
    """
    return await create_room(
        name=room_data.name,
        topic=room_data.topic,
        max_members=room_data.max_members,
        mentor=current_user
    )


@router.get("/", response_model=List[RoomResponse])
async def get_my_rooms(current_user: dict = Depends(get_current_active_user)):
    """Return all rooms the current user is a member of (mentor or student)."""
    return await get_user_rooms(current_user["_id"])


@router.get("/join/{invite_code}", response_model=RoomPreviewResponse)
async def preview_room(invite_code: str):
    """
    Preview a room before joining — no auth needed.
    Frontend shows this as the 'You've been invited to...' screen.
    """
    room = await get_room_by_invite_code(invite_code)
    return {
        "id": str(room["_id"]),
        "name": room["name"],
        "topic": room.get("topic"),
        "mentor_name": room["mentor_name"],
        "mentor_picture": room["mentor_picture"],
        "member_count": len(room.get("members", [])),
        "max_members": room["max_members"],
        "is_active": room["is_active"]
    }


@router.post("/join/{invite_code}", response_model=RoomResponse)
async def join_room_route(
    invite_code: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Student joins a room via invite link."""
    room_response = await join_room(invite_code, current_user)

    # Notify everyone already in the room via WebSocket
    room_id = room_response["id"]
    await manager.broadcast(room_id, {
        "type": "join",
        "user_id": current_user["_id"],
        "user_name": current_user["name"]
    })

    return room_response


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    room = await get_room_by_id(room_id)
    if current_user["_id"] not in room["members"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this room")
    return room_to_response(room)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room_route(
    room_id: str,
    room_update: RoomUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    update_data = room_update.dict(exclude_unset=True)
    if not update_data:
        room = await get_room_by_id(room_id)
        return room_to_response(room)
    return await update_room(room_id, update_data, current_user["_id"])


@router.delete("/{room_id}")
async def close_room_route(
    room_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Mentor closes the room. Notifies all connected members via WebSocket."""
    await close_room(room_id, current_user["_id"])

    await manager.broadcast(room_id, {"type": "room_closed"})

    return {"message": "Room closed successfully"}


# ─── Membership (HTTP) ────────────────────────────────────────────────────────

@router.delete("/{room_id}/members/{user_id}")
async def kick_member_route(
    room_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Mentor removes a student from the room."""
    await kick_member(room_id, user_id, current_user["_id"])

    # Tell the kicked user they've been removed, then tell everyone else
    await manager.send_to_user(room_id, user_id, {"type": "kick", "user_id": user_id})
    await manager.broadcast(room_id, {
        "type": "kick",
        "user_id": user_id,
        "user_name": ""   # frontend can look this up from its member list
    }, exclude_user_id=user_id)

    return {"message": "Member removed successfully"}


@router.delete("/{room_id}/leave")
async def leave_room_route(
    room_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Student voluntarily leaves a room."""
    await leave_room(room_id, current_user["_id"])

    await manager.broadcast(room_id, {
        "type": "leave",
        "user_id": current_user["_id"],
        "user_name": current_user["name"]
    })

    return {"message": "Left the room successfully"}


# ─── Messages (HTTP — for history / pagination) ───────────────────────────────

@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_room_messages(
    room_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Fetch paginated message history.
    Use this on initial room load; after that, WebSocket delivers new messages.
    """
    room = await get_room_by_id(room_id)
    if current_user["_id"] not in room["members"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this room")

    await mark_messages_read(room_id, current_user["_id"])
    return await get_messages(room_id, skip=skip, limit=limit)


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/{room_id}/ws")
async def room_websocket(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(...)     # ?token=<jwt> in the WS URL
):
    """
    Real-time messaging endpoint.

    Connect:  ws://host/api/rooms/{room_id}/ws?token=<jwt>

    The client sends JSON frames:
      { "type": "message", "content": "...", "attachment": null }
      { "type": "ping" }

    The server broadcasts JSON frames to all room members:
      { "type": "message", ...MessageResponse }
      { "type": "join" / "leave" / "kick" / "room_closed" / "presence" }
    """

    # ── Auth ──────────────────────────────────────────────────────────────────
    user = await get_ws_user(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # ── Room membership check ─────────────────────────────────────────────────
    try:
        room = await get_room_by_id(room_id)
    except HTTPException:
        await websocket.close(code=4004, reason="Room not found")
        return

    if user["_id"] not in room["members"]:
        await websocket.close(code=4003, reason="Not a member of this room")
        return

    if not room["is_active"]:
        await websocket.close(code=4000, reason="Room is closed")
        return

    # ── Connect ───────────────────────────────────────────────────────────────
    await manager.connect(websocket, room_id, user["_id"], user["name"])

    # Tell everyone a new user came online
    await manager.broadcast(room_id, {
        "type": "join",
        "user_id": user["_id"],
        "user_name": user["name"]
    }, exclude_user_id=user["_id"])

    # Send the joining user the current online presence list
    await manager.send_to_user(room_id, user["_id"], {
        "type": "presence",
        "online_users": manager.get_online_users(room_id)
    })

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "Invalid JSON"
                }))
                continue

            msg_type = data.get("type")

            # ── Ping / keep-alive ─────────────────────────────────────────────
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # ── Chat message ──────────────────────────────────────────────────
            if msg_type == "message":
                content = data.get("content", "").strip()
                attachment = data.get("attachment")

                if not content and not attachment:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "detail": "Message cannot be empty"
                    }))
                    continue

                # Re-check room is still active (mentor may have closed it)
                room = await get_room_by_id(room_id)
                if not room["is_active"]:
                    await websocket.send_text(json.dumps({"type": "room_closed"}))
                    break

                # Persist to MongoDB
                saved_msg = await save_message(room_id, user, content, attachment)

                # Broadcast to all room members (including sender)
                await manager.broadcast(room_id, {
                    "type": "message",
                    **saved_msg
                })
                continue

            # ── Unknown type ──────────────────────────────────────────────────
            await websocket.send_text(json.dumps({
                "type": "error",
                "detail": f"Unknown message type: {msg_type}"
            }))

    except WebSocketDisconnect:
        pass

    finally:
        manager.disconnect(websocket, room_id)
        # Notify remaining members this user went offline
        await manager.broadcast(room_id, {
            "type": "leave",
            "user_id": user["_id"],
            "user_name": user["name"]
        })