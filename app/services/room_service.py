"""
services/room_service.py

All MongoDB operations for rooms. The router stays thin;
business logic and DB calls live here.
"""

import secrets
from datetime import datetime
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status

from app.database import get_rooms_collection


# ─── Helpers ─────────────────────────────────────────────────────────────────

def generate_invite_code() -> str:
    """
    Generate a URL-safe random token.
    token_urlsafe(12) -> 16 base64 chars, 2^96 possible values.
    Collision probability is astronomically low but the DB unique
    index is the real safety net.
    """
    return secrets.token_urlsafe(12)


def validate_object_id(id: str, label: str = "ID") -> ObjectId:
    try:
        return ObjectId(id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label} format"
        )


def build_invite_link(invite_code: str) -> str:
    # Update this to your actual frontend URL
    return f"https://vssutvibes.in/rooms/join/{invite_code}"


def room_to_response(room: dict) -> dict:
    messages = room.get("messages", [])
    last_message = messages[-1]["content"] if messages else None
    return {
        "id": str(room["_id"]),
        "name": room["name"],
        "topic": room.get("topic"),
        "mentor_id": room["mentor_id"],
        "mentor_name": room["mentor_name"],
        "mentor_picture": room["mentor_picture"],
        "member_count": len(room.get("members", [])),
        "max_members": room["max_members"],
        "invite_code": room["invite_code"],
        "invite_link": build_invite_link(room["invite_code"]),
        "is_active": room["is_active"],
        "last_message": last_message,
        "created_at": room["created_at"]
    }


def message_to_response(msg: dict, index: int) -> dict:
    return {
        "id": str(index),
        "sender_id": msg["sender_id"],
        "sender_name": msg["sender_name"],
        "sender_picture": msg["sender_picture"],
        "content": msg["content"],
        "attachment": msg.get("attachment"),
        "sent_at": msg["sent_at"],
        "read_by_count": len(msg.get("read_by", []))
    }


# ─── Room CRUD ────────────────────────────────────────────────────────────────

async def create_room(name: str, topic: Optional[str], max_members: int, mentor: dict) -> dict:
    col = await get_rooms_collection()

    # Retry up to 5 times on the astronomically unlikely invite_code collision
    for _ in range(5):
        invite_code = generate_invite_code()
        room_doc = {
            "name": name,
            "topic": topic,
            "mentor_id": mentor["_id"],
            "mentor_name": mentor["name"],
            "mentor_picture": mentor.get("profile_picture", ""),
            "members": [mentor["_id"]],   # mentor is automatically a member
            "invite_code": invite_code,
            "messages": [],
            "max_members": max_members,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        try:
            result = await col.insert_one(room_doc)
            room_doc["_id"] = result.inserted_id
            return room_to_response(room_doc)
        except DuplicateKeyError:
            continue

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique room code. Please try again."
    )


async def get_room_by_id(room_id: str) -> dict:
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")
    room = await col.find_one({"_id": oid})
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


async def get_room_by_invite_code(invite_code: str) -> dict:
    col = await get_rooms_collection()
    room = await col.find_one({"invite_code": invite_code})
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite link")
    return room


async def get_user_rooms(user_id: str) -> list:
    col = await get_rooms_collection()
    cursor = col.find({"members": user_id}).sort("updated_at", -1)
    rooms = await cursor.to_list(length=100)
    return [room_to_response(r) for r in rooms]


async def update_room(room_id: str, update_data: dict, requesting_user_id: str) -> dict:
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")
    room = await col.find_one({"_id": oid})

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room["mentor_id"] != requesting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the mentor can update this room")

    update_data["updated_at"] = datetime.utcnow()
    await col.update_one({"_id": oid}, {"$set": update_data})
    room = await col.find_one({"_id": oid})
    return room_to_response(room)


async def close_room(room_id: str, requesting_user_id: str):
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")
    room = await col.find_one({"_id": oid})

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room["mentor_id"] != requesting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the mentor can close this room")

    await col.update_one({"_id": oid}, {"$set": {"is_active": False, "updated_at": datetime.utcnow()}})


# ─── Membership ───────────────────────────────────────────────────────────────

async def join_room(invite_code: str, user: dict) -> dict:
    col = await get_rooms_collection()
    room = await get_room_by_invite_code(invite_code)

    if not room["is_active"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This room is no longer active")

    if len(room["members"]) >= room["max_members"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is full")

    if user["_id"] in room["members"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already in this room")

    await col.update_one(
        {"_id": room["_id"]},
        {
            "$push": {"members": user["_id"]},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    room["members"].append(user["_id"])
    return room_to_response(room)


async def kick_member(room_id: str, target_user_id: str, requesting_user_id: str):
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")
    room = await col.find_one({"_id": oid})

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room["mentor_id"] != requesting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the mentor can remove members")
    if target_user_id == requesting_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor cannot remove themselves")
    if target_user_id not in room["members"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not in this room")

    await col.update_one(
        {"_id": oid},
        {
            "$pull": {"members": target_user_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )


async def leave_room(room_id: str, user_id: str):
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")
    room = await col.find_one({"_id": oid})

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room["mentor_id"] == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mentor cannot leave. Close the room instead.")
    if user_id not in room["members"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in this room")

    await col.update_one(
        {"_id": oid},
        {
            "$pull": {"members": user_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )


# ─── Messages ─────────────────────────────────────────────────────────────────

async def save_message(room_id: str, sender: dict, content: str, attachment: Optional[str] = None) -> dict:
    """Persist a message to MongoDB and return it as a response dict."""
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")

    message = {
        "sender_id": sender["_id"],
        "sender_name": sender["name"],
        "sender_picture": sender.get("profile_picture", ""),
        "content": content,
        "attachment": attachment,
        "sent_at": datetime.utcnow(),
        "read_by": [sender["_id"]]
    }

    # Push message and update timestamp atomically
    result = await col.find_one_and_update(
        {"_id": oid},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": datetime.utcnow()}
        },
        return_document=True
    )

    # The index of the new message is the last one
    msg_index = len(result["messages"]) - 1
    return message_to_response(message, msg_index)


async def get_messages(room_id: str, skip: int = 0, limit: int = 50) -> list:
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")

    # Use MongoDB slice to fetch a page of messages efficiently
    room = await col.find_one(
        {"_id": oid},
        {"messages": {"$slice": [skip, limit]}}
    )
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    return [message_to_response(msg, skip + i) for i, msg in enumerate(room.get("messages", []))]


async def mark_messages_read(room_id: str, user_id: str):
    """Mark all messages in a room as read by this user."""
    col = await get_rooms_collection()
    oid = validate_object_id(room_id, "room ID")
    await col.update_one(
        {"_id": oid},
        {"$addToSet": {"messages.$[].read_by": user_id}}
    )


# ─── DB Index Setup (call once on startup) ───────────────────────────────────

async def create_room_indexes():
    col = await get_rooms_collection()
    await col.create_index("invite_code", unique=True)
    await col.create_index("mentor_id")
    await col.create_index("members")
    await col.create_index("updated_at")
    print("Room indexes created.")
