from bson import ObjectId
from app.db.database import get_users_collection, get_rooms_collection


async def fetch_user_rooms(user_id: str) -> list[dict]:
    """Return all active rooms the user is a member of."""
    col    = await get_rooms_collection()
    cursor = col.find(
        {"members": user_id, "is_active": True},
        {"_id": 1, "name": 1, "members": 1}
    )
    return await cursor.to_list(length=100)


async def fetch_candidates(exclude_ids: set[str], limit: int = 500) -> list[dict]:
    """
    Fetch users who are not in exclude_ids (self + existing connections).
    Projects only the fields needed for scoring.
    """
    col          = await get_users_collection()
    exclude_oids = [ObjectId(e) for e in exclude_ids if ObjectId.is_valid(e)]

    cursor = col.find(
        {"_id": {"$nin": exclude_oids}},
        {
            "_id": 1, "name": 1, "registration_number": 1,
            "department": 1, "profile_picture": 1, "is_alumni": 1,
            "skills": 1, "year_of_study": 1, "connections": 1
        }
    )
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def fetch_by_department(
    department:  str,
    exclude_ids: set[str],
    limit:       int
) -> list[dict]:
    """Fetch users in a specific department, excluding given IDs."""
    col          = await get_users_collection()
    exclude_oids = [ObjectId(e) for e in exclude_ids if ObjectId.is_valid(e)]

    cursor = col.find(
        {
            "_id":        {"$nin": exclude_oids},
            "department": department
        },
        {
            "_id": 1, "name": 1, "registration_number": 1,
            "department": 1, "profile_picture": 1, "is_alumni": 1,
            "skills": 1, "year_of_study": 1
        }
    ).limit(limit)

    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def fetch_by_skills(
    skills:      list[str],
    exclude_ids: set[str],
    limit:       int
) -> list[dict]:
    """
    Fetch users who share at least one skill.
    Over-fetches (limit * 2) so the service can re-rank by overlap count.
    """
    col          = await get_users_collection()
    exclude_oids = [ObjectId(e) for e in exclude_ids if ObjectId.is_valid(e)]

    cursor = col.find(
        {
            "_id":    {"$nin": exclude_oids},
            "skills": {"$in": skills}
        },
        {
            "_id": 1, "name": 1, "registration_number": 1,
            "department": 1, "profile_picture": 1, "is_alumni": 1,
            "skills": 1, "year_of_study": 1
        }
    ).limit(limit * 2)

    docs = await cursor.to_list(length=limit * 2)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs