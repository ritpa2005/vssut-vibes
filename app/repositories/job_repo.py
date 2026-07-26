from bson import ObjectId
from bson.errors import InvalidId
from typing import Optional
from datetime import datetime

from app.db.database import get_jobs_collection


def parse_job_id(job_id: str) -> ObjectId:
    try:
        return ObjectId(job_id)
    except InvalidId:
        raise InvalidId(f"Invalid job ID format: {job_id}")


async def insert(job_dict: dict) -> str:
    col    = await get_jobs_collection()
    result = await col.insert_one(job_dict)
    return str(result.inserted_id)


async def find_by_id(job_id: str) -> dict | None:
    col = await get_jobs_collection()
    oid = parse_job_id(job_id)
    job = await col.find_one({"_id": oid})
    if job:
        job["_id"] = str(job["_id"])
    return job


async def find_many(
    job_type:  Optional[str],
    location:  Optional[str],
    company:   Optional[str],
    search:    Optional[str],
    skip:      int,
    limit:     int
) -> list[dict]:
    col     = await get_jobs_collection()
    filters = {"is_active": True}

    if job_type:
        filters["type"] = job_type
    if location:
        filters["location"] = {"$regex": location, "$options": "i"}
    if company:
        filters["company"] = {"$regex": company, "$options": "i"}
    if search:
        filters["$or"] = [
            {"title":       {"$regex": search, "$options": "i"}},
            {"company":     {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    cursor = col.find(filters).sort("posted_date", -1).skip(skip).limit(limit)
    jobs   = await cursor.to_list(length=limit)
    for j in jobs:
        j["_id"] = str(j["_id"])
    return jobs


async def increment_views(job_id: str) -> None:
    col = await get_jobs_collection()
    oid = parse_job_id(job_id)
    await col.update_one({"_id": oid}, {"$inc": {"views": 1}})


async def update_by_id(job_id: str, update_data: dict) -> dict:
    col = await get_jobs_collection()
    oid = parse_job_id(job_id)
    await col.update_one({"_id": oid}, {"$set": update_data})
    job = await col.find_one({"_id": oid})
    job["_id"] = str(job["_id"])
    return job


async def set_inactive(job_id: str) -> None:
    col = await get_jobs_collection()
    oid = parse_job_id(job_id)
    await col.update_one({"_id": oid}, {"$set": {"is_active": False}})


async def push_applicant(job_id: str, user_id: str) -> None:
    col = await get_jobs_collection()
    oid = parse_job_id(job_id)
    await col.update_one({"_id": oid}, {"$push": {"applicants": user_id}})