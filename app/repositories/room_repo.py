import secrets
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from app.db.database import get_rooms_collection


def generate_invite_code() -> str:
    return secrets.token_urlsafe(12)


def parse_room_id(room_id: str) -> ObjectId:
    try:
        return ObjectId(room_id)
    except InvalidId:
        raise InvalidId(f"Invalid room ID format: {room_id}")


async def insert_room(room_doc: dict) -> str:
    col    = await get_rooms_collection()
    result = await col.insert_one(room_doc)
    return str(result.inserted_id)

async def find_by_id(room_id: str) -> dict | None:
    col  = await get_rooms_collection()
    oid  = parse_room_id(room_id)
    room = await col.find_one({"_id": oid})
    return room

async def find_by_invite_code(invite_code: str) -> dict | None:
    col = await get_rooms_collection()
    return await col.find_one({"invite_code": invite_code})

async def find_by_member(user_id: str) -> list[dict]:
    col    = await get_rooms_collection()
    cursor = col.find({"members": user_id}).sort("updated_at", -1)
    return await cursor.to_list(length=100)

async def update_by_id(room_id: str, update_data: dict) -> dict:
    col = await get_rooms_collection()
    oid = parse_room_id(room_id)
    update_data["updated_at"] = datetime.utcnow()
    await col.update_one({"_id": oid}, {"$set": update_data})
    return await col.find_one({"_id": oid})

async def set_inactive(room_id: str) -> None:
    col = await get_rooms_collection()
    oid = parse_room_id(room_id)
    await col.update_one(
        {"_id": oid},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )


async def push_member(room_id: ObjectId, user_id: str) -> None:
    col = await get_rooms_collection()
    await col.update_one(
        {"_id": room_id},
        {
            "$push": {"members": user_id},
            "$set":  {"updated_at": datetime.utcnow()}
        }
    )

async def pull_member(room_id: str, user_id: str) -> None:
    col = await get_rooms_collection()
    oid = parse_room_id(room_id)
    await col.update_one(
        {"_id": oid},
        {
            "$pull": {"members": user_id},
            "$set":  {"updated_at": datetime.utcnow()}
        }
    )


async def insert_message(room_id: str, message: dict) -> dict:
    """
    Atomically push message and return the updated room document.
    """
    col    = await get_rooms_collection()
    oid    = parse_room_id(room_id)
    result = await col.find_one_and_update(
        {"_id": oid},
        {
            "$push": {"messages": message},
            "$set":  {"updated_at": datetime.utcnow()}
        },
        return_document=True
    )
    return result

async def fetch_messages(room_id: str, skip: int, limit: int) -> list[dict]:
    """Fetch a page of messages using MongoDB $slice."""
    col  = await get_rooms_collection()
    oid  = parse_room_id(room_id)
    room = await col.find_one(
        {"_id": oid},
        {"messages": {"$slice": [skip, limit]}}
    )
    return room.get("messages", []) if room else []

async def add_read_by(room_id: str, user_id: str) -> None:
    """Mark all messages in a room as read by user_id."""
    col = await get_rooms_collection()
    oid = parse_room_id(room_id)
    await col.update_one(
        {"_id": oid},
        {"$addToSet": {"messages.$[].read_by": user_id}}
    )
