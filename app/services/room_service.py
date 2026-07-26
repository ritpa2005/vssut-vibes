from datetime import datetime
from typing import Optional
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    InternalException,
)
from app.repositories import room_repo
from app.schemas.room import (
    room_to_response,
    message_to_response,
)

async def create(name: str, topic: Optional[str], max_members: int, mentor: dict) -> dict:
    """
    Create a room with a unique invite code.
    Retries up to 5 times on the astronomically unlikely collision.
    """
    for _ in range(5):
        invite_code = room_repo.generate_invite_code()
        room_doc = {
            "name":           name,
            "topic":          topic,
            "mentor_id":      mentor["_id"],
            "mentor_name":    mentor["name"],
            "mentor_picture": mentor.get("profile_picture", ""),
            "members":        [mentor["_id"]],
            "invite_code":    invite_code,
            "messages":       [],
            "max_members":    max_members,
            "is_active":      True,
            "created_at":     datetime.utcnow(),
            "updated_at":     datetime.utcnow(),
        }
        try:
            inserted_id       = await room_repo.insert_room(room_doc)
            room_doc["_id"]   = inserted_id
            return room_to_response(room_doc)
        except DuplicateKeyError:
            continue

    raise InternalException("Could not generate a unique room code. Please try again.")


async def get_by_id(room_id: str) -> dict:
    try:
        room = await room_repo.find_by_id(room_id)
    except InvalidId:
        raise BadRequestException("Invalid room ID format")

    if not room:
        raise NotFoundException("Room")
    return room


async def get_by_invite_code(invite_code: str) -> dict:
    room = await room_repo.find_by_invite_code(invite_code)
    if not room:
        raise NotFoundException("Room")
    return room


async def get_user_rooms(user_id: str) -> list[dict]:
    rooms = await room_repo.find_by_member(user_id)
    return [room_to_response(r) for r in rooms]


async def update(room_id: str, update_data: dict, requesting_user_id: str) -> dict:
    room = await get_by_id(room_id)

    if room["mentor_id"] != requesting_user_id:
        raise ForbiddenException("Only the mentor can update this room")

    updated = await room_repo.update_by_id(room_id, update_data)
    return room_to_response(updated)


async def close(room_id: str, requesting_user_id: str) -> None:
    room = await get_by_id(room_id)

    if room["mentor_id"] != requesting_user_id:
        raise ForbiddenException("Only the mentor can close this room")

    await room_repo.set_inactive(room_id)


# ── Membership ────────────────────────────────────────────────────────────────

async def join(invite_code: str, user: dict) -> dict:
    room = await get_by_invite_code(invite_code)

    if not room["is_active"]:
        raise BadRequestException("This room is no longer active")
    if len(room["members"]) >= room["max_members"]:
        raise BadRequestException("Room is full")
    if user["_id"] in room["members"]:
        raise BadRequestException("You are already in this room")

    await room_repo.push_member(room["_id"], user["_id"])
    room["members"].append(user["_id"])
    return room_to_response(room)


async def kick(room_id: str, target_user_id: str, requesting_user_id: str) -> None:
    room = await get_by_id(room_id)

    if room["mentor_id"] != requesting_user_id:
        raise ForbiddenException("Only the mentor can remove members")
    if target_user_id == requesting_user_id:
        raise BadRequestException("Mentor cannot remove themselves")
    if target_user_id not in room["members"]:
        raise BadRequestException("User is not in this room")

    await room_repo.pull_member(room_id, target_user_id)


async def leave(room_id: str, user_id: str) -> None:
    room = await get_by_id(room_id)

    if room["mentor_id"] == user_id:
        raise BadRequestException("Mentor cannot leave. Close the room instead.")
    if user_id not in room["members"]:
        raise BadRequestException("You are not in this room")

    await room_repo.pull_member(room_id, user_id)


# ── Messages ──────────────────────────────────────────────────────────────────

async def save_message(
    room_id:    str,
    sender:     dict,
    content:    str,
    attachment: Optional[str] = None
) -> dict:
    message = {
        "sender_id":      sender["_id"],
        "sender_name":    sender["name"],
        "sender_picture": sender.get("profile_picture", ""),
        "content":        content,
        "attachment":     attachment,
        "sent_at":        datetime.utcnow(),
        "read_by":        [sender["_id"]],
    }
    result    = await room_repo.insert_message(room_id, message)
    msg_index = len(result["messages"]) - 1
    return message_to_response(message, msg_index)


async def get_messages(room_id: str, skip: int, limit: int) -> list[dict]:
    msgs = await room_repo.fetch_messages(room_id, skip, limit)
    return [message_to_response(msg, skip + i) for i, msg in enumerate(msgs)]


async def mark_read(room_id: str, user_id: str) -> None:
    await room_repo.add_read_by(room_id, user_id)