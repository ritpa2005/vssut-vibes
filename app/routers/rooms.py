from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from typing import List
import json

from app.schemas.room import (
    RoomCreate, RoomUpdate,
    RoomResponse, RoomPreviewResponse, MessageResponse
)
from app.core.dependencies import get_current_active_user
from app.core.exceptions import ForbiddenException
from app.core.ws_manager import manager
from app.services import room_service
from app.services.ws_handler import get_ws_user

router = APIRouter(prefix="/rooms", tags=["Collaboration Rooms"])


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data:    RoomCreate,
    current_user: dict = Depends(get_current_active_user)
):
    return await room_service.create(
        name=room_data.name,
        topic=room_data.topic,
        max_members=room_data.max_members,
        mentor=current_user
    )


@router.get("/", response_model=List[RoomResponse])
async def get_my_rooms(current_user: dict = Depends(get_current_active_user)):
    return await room_service.get_user_rooms(current_user["_id"])


@router.get("/join/{invite_code}", response_model=RoomPreviewResponse)
async def preview_room(invite_code: str):
    """No auth required — shown on the invite landing page."""
    room = await room_service.get_by_invite_code(invite_code)
    return {
        "id":             str(room["_id"]),
        "name":           room["name"],
        "topic":          room.get("topic"),
        "mentor_name":    room["mentor_name"],
        "mentor_picture": room["mentor_picture"],
        "member_count":   len(room.get("members", [])),
        "max_members":    room["max_members"],
        "is_active":      room["is_active"],
    }


@router.post("/join/{invite_code}", response_model=RoomResponse)
async def join_room(
    invite_code:  str,
    current_user: dict = Depends(get_current_active_user)
):
    room_response = await room_service.join(invite_code, current_user)

    await manager.broadcast(room_response["id"], {
        "type":      "join",
        "user_id":   current_user["_id"],
        "user_name": current_user["name"],
    })
    return room_response


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    room = await room_service.get_by_id(room_id)
    if current_user["_id"] not in room["members"]:
        raise ForbiddenException("You are not a member of this room")
    from app.schemas.room import room_to_response
    return room_to_response(room)


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id:      str,
    room_update:  RoomUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    update_data = room_update.dict(exclude_unset=True)
    if not update_data:
        room = await room_service.get_by_id(room_id)
        from app.schemas.room import room_to_response
        return room_to_response(room)
    return await room_service.update(room_id, update_data, current_user["_id"])


@router.delete("/{room_id}")
async def close_room(
    room_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    await room_service.close(room_id, current_user["_id"])
    await manager.broadcast(room_id, {"type": "room_closed"})
    return {"message": "Room closed successfully"}


@router.delete("/{room_id}/members/{user_id}")
async def kick_member(
    room_id:      str,
    user_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    await room_service.kick(room_id, user_id, current_user["_id"])
    await manager.send_to_user(room_id, user_id, {"type": "kick", "user_id": user_id})
    await manager.broadcast(room_id, {"type": "kick", "user_id": user_id, "user_name": ""}, exclude_user_id=user_id)
    return {"message": "Member removed successfully"}


@router.delete("/{room_id}/leave")
async def leave_room(
    room_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    await room_service.leave(room_id, current_user["_id"])
    await manager.broadcast(room_id, {
        "type":      "leave",
        "user_id":   current_user["_id"],
        "user_name": current_user["name"],
    })
    return {"message": "Left the room successfully"}


@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_room_messages(
    room_id:      str,
    skip:         int  = Query(0,  ge=0),
    limit:        int  = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user)
):
    room = await room_service.get_by_id(room_id)
    if current_user["_id"] not in room["members"]:
        raise ForbiddenException("You are not a member of this room")

    await room_service.mark_read(room_id, current_user["_id"])
    return await room_service.get_messages(room_id, skip=skip, limit=limit)


# ══════════════════════════════════════════════════════════════
# WebSocket
# Connect: ws://host/api/rooms/{room_id}/ws?token=<jwt>
#
# Client MUST send a ping every 30 seconds to stay connected.
# Server closes the connection after 5 minutes of silence (code 4008).

# Client → Server frames:
#   { "type": "message", "content": "...", "attachment": null }
#   { "type": "ping" }        - keepalive
#
# Server → Client frames:
#   { "type": "message",  ...MessageResponse }
#   { "type": "join",     "user_id", "user_name" }
#   { "type": "leave",    "user_id", "user_name" }
#   { "type": "kick",     "user_id" }
#   { "type": "presence", "online_users": [...] }
#   { "type": "room_closed" }
#   { "type": "pong" }         - ping acknowledged
#   { "type": "error",    "detail": "..." }
# ══════════════════════════════════════════════════════════════

@router.websocket("/{room_id}/ws")
async def room_websocket(
    websocket: WebSocket,
    room_id:   str,
    token:     str = Query(...)
):
    # Auth
    user = await get_ws_user(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Room validation
    try:
        room = await room_service.get_by_id(room_id)
    except Exception:
        await websocket.close(code=4004, reason="Room not found")
        return

    if user["_id"] not in room["members"]:
        await websocket.close(code=4003, reason="Not a member of this room")
        return

    if not room["is_active"]:
        await websocket.close(code=4000, reason="Room is closed")
        return

    # connect() also starts the watchdog task for this connection
    await manager.connect(websocket, room_id, user["_id"], user["name"])

    await manager.broadcast(room_id, {
        "type":      "join",
        "user_id":   user["_id"],
        "user_name": user["name"],
    }, exclude_user_id=user["_id"])

    await manager.send_to_user(room_id, user["_id"], {
        "type":         "presence",
        "online_users": manager.get_online_users(room_id),
    })

    # Message loop
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "Invalid JSON"}))
                continue

            msg_type = data.get("type")

            # Ping / keepalive
            if msg_type == "ping":
                # Reset the 5-minute watchdog timer for this connection
                manager.update_ping(websocket, room_id)
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # Chat message
            if msg_type == "message":
                content    = data.get("content", "").strip()
                attachment = data.get("attachment")

                if not content and not attachment:
                    await websocket.send_text(json.dumps({"type": "error", "detail": "Message cannot be empty"}))
                    continue

                # Re-check room is still active
                room = await room_service.get_by_id(room_id)
                if not room["is_active"]:
                    await websocket.send_text(json.dumps({"type": "room_closed"}))
                    break

                saved_msg = await room_service.save_message(room_id, user, content, attachment)
                await manager.broadcast(room_id, {"type": "message", **saved_msg})
                continue

            # Unknown frame
            await websocket.send_text(json.dumps({
                "type":   "error",
                "detail": f"Unknown message type: {msg_type}"
            }))

    except WebSocketDisconnect:
        pass

    finally:
        # disconnect() also cancels the watchdog task
        manager.disconnect(websocket, room_id)
        await manager.broadcast(room_id, {
            "type":      "leave",
            "user_id":   user["_id"],
            "user_name": user["name"],
        })