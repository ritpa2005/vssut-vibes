from app.db.database import get_users_collection, get_rooms_collection
from bson import ObjectId
from typing import Optional

W_DEPARTMENT  = 30
W_SKILL       = 10
W_SKILL_CAP   = 50
W_ROOM        = 25
W_ROOM_CAP    = 75
W_ALUMNI      = 10

async def get_suggestions(current_user: dict, limit: int = 10) -> list[dict]:
    users_col = await get_users_collection()
    rooms_col = await get_rooms_collection()

    user_id          = current_user["_id"]
    my_connections   = set(current_user.get("connections", []))
    my_skills        = set(s.lower() for s in current_user.get("skills", []))
    my_department    = current_user.get("department", "")
    my_is_alumni     = current_user.get("is_alumni", False)

    my_rooms_cursor = rooms_col.find(
        {"members": user_id, "is_active": True},
        {"_id": 1, "name": 1, "members": 1}
    )
    my_rooms = await my_rooms_cursor.to_list(length=100)

    my_room_map: dict[str, str] = {str(r["_id"]): r["name"] for r in my_rooms}

    shared_rooms_by_user: dict[str, set] = {}
    for room in my_rooms:
        for member_id in room.get("members", []):
            mid = str(member_id)
            if mid == user_id:
                continue
            shared_rooms_by_user.setdefault(mid, set()).add(room["name"])

    exclude_ids = my_connections | {user_id}
    exclude_oids = [ObjectId(eid) for eid in exclude_ids if ObjectId.is_valid(eid)]

    candidate_cursor = users_col.find(
        {"_id": {"$nin": exclude_oids}},
        {
            "_id": 1, "name": 1, "registration_number": 1,
            "department": 1, "profile_picture": 1, "is_alumni": 1,
            "skills": 1, "bio": 1, "year_of_study": 1,
            "connections": 1
        }
    )
    candidates = await candidate_cursor.to_list(length=500)

    scored = []
    for c in candidates:
        cid           = str(c["_id"])
        score         = 0
        match_reasons = []

        if c.get("department") == my_department:
            score += W_DEPARTMENT
            match_reasons.append(f"Same department: {my_department}")

        their_skills   = set(s.lower() for s in c.get("skills", []))
        common_skills  = my_skills & their_skills
        if common_skills:
            skill_score = min(len(common_skills) * W_SKILL, W_SKILL_CAP)
            score      += skill_score
            readable    = ", ".join(s.title() for s in list(common_skills)[:3])
            match_reasons.append(
                f"{len(common_skills)} shared skill{'s' if len(common_skills) > 1 else ''}: {readable}"
            )

        shared_rooms = shared_rooms_by_user.get(cid, set())
        if shared_rooms:
            room_score = min(len(shared_rooms) * W_ROOM, W_ROOM_CAP)
            score     += room_score
            readable   = ", ".join(list(shared_rooms)[:2])
            match_reasons.append(
                f"In {len(shared_rooms)} shared room{'s' if len(shared_rooms) > 1 else ''}: {readable}"
            )

        their_is_alumni = c.get("is_alumni", False)
        if my_is_alumni != their_is_alumni:
            score += W_ALUMNI
            if my_is_alumni:
                match_reasons.append("Student you could mentor")
            else:
                match_reasons.append("Alumni who may mentor you")

        if score > 0:
            scored.append({
                "id":                  cid,
                "name":                c["name"],
                "registration_number": c["registration_number"],
                "department":          c.get("department", ""),
                "profile_picture":     c.get("profile_picture", ""),
                "is_alumni":           c.get("is_alumni", False),
                "year_of_study":       c.get("year_of_study"),
                "skills":              c.get("skills", []),
                "mutual_connections":  len(set(str(x) for x in c.get("connections", [])) & my_connections),
                "match_score":         score,
                "match_reasons":       match_reasons,
            })

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:limit]


async def get_suggestions_by_department(current_user: dict, limit: int = 10) -> list[dict]:
    users_col      = await get_users_collection()
    my_connections = set(current_user.get("connections", []))
    exclude_ids    = my_connections | {current_user["_id"]}
    exclude_oids   = [ObjectId(e) for e in exclude_ids if ObjectId.is_valid(e)]

    cursor = users_col.find(
        {
            "_id":        {"$nin": exclude_oids},
            "department": current_user.get("department", "")
        },
        {"_id": 1, "name": 1, "registration_number": 1, "department": 1,
         "profile_picture": 1, "is_alumni": 1, "skills": 1, "year_of_study": 1}
    ).limit(limit)

    docs = await cursor.to_list(length=limit)
    return [
        {
            "id":                  str(d["_id"]),
            "name":                d["name"],
            "registration_number": d["registration_number"],
            "department":          d.get("department", ""),
            "profile_picture":     d.get("profile_picture", ""),
            "is_alumni":           d.get("is_alumni", False),
            "year_of_study":       d.get("year_of_study"),
            "skills":              d.get("skills", []),
            "mutual_connections":  0,
            "match_score":         W_DEPARTMENT,
            "match_reasons":       [f"Same department: {d.get('department', '')}"],
        }
        for d in docs
    ]


async def get_suggestions_by_skills(current_user: dict, limit: int = 10) -> list[dict]:
    users_col      = await get_users_collection()
    my_skills      = current_user.get("skills", [])
    my_connections = set(current_user.get("connections", []))

    if not my_skills:
        return []

    exclude_ids  = my_connections | {current_user["_id"]}
    exclude_oids = [ObjectId(e) for e in exclude_ids if ObjectId.is_valid(e)]

    cursor = users_col.find(
        {
            "_id":    {"$nin": exclude_oids},
            "skills": {"$in": my_skills}          # at least one skill in common
        },
        {"_id": 1, "name": 1, "registration_number": 1, "department": 1,
         "profile_picture": 1, "is_alumni": 1, "skills": 1, "year_of_study": 1}
    ).limit(limit * 2)   # over-fetch so we can sort by overlap count

    docs   = await cursor.to_list(length=limit * 2)
    my_set = set(s.lower() for s in my_skills)

    results = []
    for d in docs:
        their_set    = set(s.lower() for s in d.get("skills", []))
        common       = my_set & their_set
        readable     = ", ".join(s.title() for s in list(common)[:3])
        results.append({
            "id":                  str(d["_id"]),
            "name":                d["name"],
            "registration_number": d["registration_number"],
            "department":          d.get("department", ""),
            "profile_picture":     d.get("profile_picture", ""),
            "is_alumni":           d.get("is_alumni", False),
            "year_of_study":       d.get("year_of_study"),
            "skills":              d.get("skills", []),
            "mutual_connections":  0,
            "match_score":         min(len(common) * W_SKILL, W_SKILL_CAP),
            "match_reasons":       [f"{len(common)} shared skill{'s' if len(common)>1 else ''}: {readable}"],
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:limit]