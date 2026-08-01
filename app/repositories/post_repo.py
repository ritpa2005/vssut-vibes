from bson import ObjectId
from datetime import datetime

from app.db.database import get_posts_collection


async def insert(post_dict: dict) -> str:
    """Insert a post document, return inserted ID as string."""
    col    = await get_posts_collection()
    result = await col.insert_one(post_dict)
    return str(result.inserted_id)

async def find_by_id(post_id: str) -> dict | None:
    col  = await get_posts_collection()
    post = await col.find_one({"_id": ObjectId(post_id)})
    if post:
        post["_id"] = str(post["_id"])
    return post


async def find_feed(skip: int, limit: int) -> list[dict]:
    col    = await get_posts_collection()
    cursor = col.find().sort("created_at", -1).skip(skip).limit(limit)
    posts  = await cursor.to_list(length=limit)
    for p in posts:
        p["_id"] = str(p["_id"])
    return posts


async def find_by_author(author_id: str, skip: int, limit: int) -> list[dict]:
    col    = await get_posts_collection()
    cursor = col.find({"author_id": author_id}).sort("created_at", -1).skip(skip).limit(limit)
    posts  = await cursor.to_list(length=limit)
    for p in posts:
        p["_id"] = str(p["_id"])
    return posts


async def update_by_id(post_id: str, update_data: dict) -> dict:
    col = await get_posts_collection()
    oid = ObjectId(post_id)
    update_data["updated_at"] = datetime.utcnow()
    await col.update_one({"_id": oid}, {"$set": update_data})
    post = await col.find_one({"_id": oid})
    post["_id"] = str(post["_id"])
    return post

async def delete_by_id(post_id: str) -> None:
    col = await get_posts_collection()
    await col.delete_one({"_id": ObjectId(post_id)})


async def push_like(post_id: str, user_id: str) -> None:
    col = await get_posts_collection()
    await col.update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"likes": user_id}}
    )

async def pull_like(post_id: str, user_id: str) -> None:
    col = await get_posts_collection()
    await col.update_one(
        {"_id": ObjectId(post_id)},
        {"$pull": {"likes": user_id}}
    )

async def push_comment(post_id: str, comment: dict) -> None:
    col = await get_posts_collection()
    await col.update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"comments": comment}}
    )