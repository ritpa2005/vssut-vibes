from bson import ObjectId
from datetime import datetime
from typing import Optional

from app.db.database import get_users_collection


async def find_by_id(user_id: str) -> dict | None:
    col  = await get_users_collection()
    user = await col.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
    return user

async def find_many(
    query:      Optional[str],
    department: Optional[str],
    skip:       int,
    limit:      int
) -> list[dict]:
    col     = await get_users_collection()
    filters = {}

    if query:
        filters["$or"] = [
            {"name":                {"$regex": query, "$options": "i"}},
            {"registration_number": {"$regex": query, "$options": "i"}}
        ]
    if department:
        filters["department"] = department

    cursor = col.find(filters).skip(skip).limit(limit)
    users  = await cursor.to_list(length=limit)
    for u in users:
        u["_id"] = str(u["_id"])
    return users

async def update_by_id(user_id: str, update_data: dict) -> dict:
    col = await get_users_collection()
    oid = ObjectId(user_id)
    update_data["updated_at"] = datetime.utcnow()
    await col.update_one({"_id": oid}, {"$set": update_data})
    user = await col.find_one({"_id": oid})
    user["_id"] = str(user["_id"])
    return user


async def push_connection(user_id: str, connection_id: str) -> None:
    col = await get_users_collection()
    await col.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"connections": connection_id}}
    )

async def pull_connection(user_id: str, connection_id: str) -> None:
    col = await get_users_collection()
    await col.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"connections": connection_id}}
    )