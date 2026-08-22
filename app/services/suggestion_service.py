from app.core.cache import cache, CacheKey, CacheTTL
from app.repositories import suggestion_repo
from app.services.suggestions_scorer import (
    build_shared_rooms_map,
    rank_candidates,
    rank_by_department,
    rank_by_skills,
)


async def get_suggestions(current_user: dict, limit: int = 10) -> list[dict]:
    key    = CacheKey.suggestions(current_user["_id"])
    cached = await cache.get(key)

    if cached is not None:
        return cached[:limit]

    user_id        = current_user["_id"]
    my_connections = set(current_user.get("connections", []))
    my_skills      = set(s.lower() for s in current_user.get("skills", []))
    my_department  = current_user.get("department", "")
    my_is_alumni   = current_user.get("is_alumni", False)
    exclude_ids    = my_connections | {user_id}

    rooms      = await suggestion_repo.fetch_user_rooms(user_id)
    candidates = await suggestion_repo.fetch_candidates(exclude_ids)

    shared_rooms_map = build_shared_rooms_map(rooms, user_id)
    results = rank_candidates(
        candidates       = candidates,
        my_skills        = my_skills,
        my_department    = my_department,
        my_is_alumni     = my_is_alumni,
        my_connections   = my_connections,
        shared_rooms_map = shared_rooms_map,
        limit            = 50,
    )

    await cache.set(key, results, ttl=CacheTTL.SUGGESTIONS)
    return results[:limit]

async def get_suggestions_by_department(current_user: dict, limit: int = 10) -> list[dict]:
    key    = CacheKey.suggestions_dept(current_user["_id"])
    cached = await cache.get(key)

    if cached is not None:
        return cached[:limit]

    my_connections = set(current_user.get("connections", []))
    exclude_ids    = my_connections | {current_user["_id"]}
    department     = current_user.get("department", "")

    docs    = await suggestion_repo.fetch_by_department(department, exclude_ids, 50)
    results = rank_by_department(docs, department)

    await cache.set(key, results, ttl=CacheTTL.SUGGESTIONS)
    return results[:limit]

async def get_suggestions_by_skills(current_user: dict, limit: int = 10) -> list[dict]:
    my_skills = current_user.get("skills", [])
    if not my_skills:
        return []

    key    = CacheKey.suggestions_skills(current_user["_id"])
    cached = await cache.get(key)

    if cached is not None:
        return cached[:limit]

    my_connections = set(current_user.get("connections", []))
    exclude_ids    = my_connections | {current_user["_id"]}
    my_set         = set(s.lower() for s in my_skills)

    docs    = await suggestion_repo.fetch_by_skills(my_skills, exclude_ids, 50)
    results = rank_by_skills(docs, my_set, 50)

    await cache.set(key, results, ttl=CacheTTL.SUGGESTIONS)
    return results[:limit]