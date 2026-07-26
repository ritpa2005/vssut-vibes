# app/services/suggestion_scorer.py
#
# Responsibility: scoring logic only.
# Pure functions — no DB calls, no HTTP, no FastAPI.
# Takes raw dicts from the repo and returns scored results.
# Isolated here so it can be unit tested without any DB or HTTP mocks.

# ── Weights ───────────────────────────────────────────────────────────────────
W_DEPARTMENT = 30
W_SKILL      = 10
W_SKILL_CAP  = 50
W_ROOM       = 25
W_ROOM_CAP   = 75
W_ALUMNI     = 10


# ── Room map builder ──────────────────────────────────────────────────────────

def build_shared_rooms_map(
    rooms:   list[dict],
    user_id: str
) -> dict[str, set]:
    """
    Given a list of room docs the current user is in,
    return a map of  other_user_id → {room_name, ...}
    so we know which rooms each candidate shares with the current user.
    """
    shared: dict[str, set] = {}
    for room in rooms:
        for member_id in room.get("members", []):
            mid = str(member_id)
            if mid == user_id:
                continue
            shared.setdefault(mid, set()).add(room["name"])
    return shared


# ── Single candidate scorer ───────────────────────────────────────────────────

def score_candidate(
    candidate:       dict,
    my_skills:       set[str],
    my_department:   str,
    my_is_alumni:    bool,
    my_connections:  set[str],
    shared_rooms_map: dict[str, set]
) -> dict | None:
    """
    Score one candidate against the current user across all signals.
    Returns a scored dict or None if the candidate has no matching signal.
    """
    cid           = candidate["_id"]
    score         = 0
    match_reasons = []

    # — Department —
    if candidate.get("department") == my_department:
        score += W_DEPARTMENT
        match_reasons.append(f"Same department: {my_department}")

    # — Skills —
    their_skills  = set(s.lower() for s in candidate.get("skills", []))
    common_skills = my_skills & their_skills
    if common_skills:
        skill_score = min(len(common_skills) * W_SKILL, W_SKILL_CAP)
        score      += skill_score
        readable    = ", ".join(s.title() for s in list(common_skills)[:3])
        match_reasons.append(
            f"{len(common_skills)} shared skill"
            f"{'s' if len(common_skills) > 1 else ''}: {readable}"
        )

    # — Shared rooms —
    shared_rooms = shared_rooms_map.get(cid, set())
    if shared_rooms:
        room_score = min(len(shared_rooms) * W_ROOM, W_ROOM_CAP)
        score     += room_score
        readable   = ", ".join(list(shared_rooms)[:2])
        match_reasons.append(
            f"In {len(shared_rooms)} shared room"
            f"{'s' if len(shared_rooms) > 1 else ''}: {readable}"
        )

    # — Alumni ↔ student cross-match —
    their_is_alumni = candidate.get("is_alumni", False)
    if my_is_alumni != their_is_alumni:
        score += W_ALUMNI
        match_reasons.append(
            "Student you could mentor" if my_is_alumni
            else "Alumni who may mentor you"
        )

    if score == 0:
        return None   # no signal — exclude from results

    mutual = len(
        set(str(x) for x in candidate.get("connections", [])) & my_connections
    )

    return {
        "id":                  cid,
        "name":                candidate["name"],
        "registration_number": candidate["registration_number"],
        "department":          candidate.get("department", ""),
        "profile_picture":     candidate.get("profile_picture", ""),
        "is_alumni":           candidate.get("is_alumni", False),
        "year_of_study":       candidate.get("year_of_study"),
        "skills":              candidate.get("skills", []),
        "mutual_connections":  mutual,
        "match_score":         score,
        "match_reasons":       match_reasons,
    }


# ── Batch scorers ─────────────────────────────────────────────────────────────

def rank_candidates(
    candidates:      list[dict],
    my_skills:       set[str],
    my_department:   str,
    my_is_alumni:    bool,
    my_connections:  set[str],
    shared_rooms_map: dict[str, set],
    limit:           int
) -> list[dict]:
    """Score and rank a list of candidates, returning the top `limit`."""
    scored = []
    for c in candidates:
        result = score_candidate(
            c, my_skills, my_department,
            my_is_alumni, my_connections, shared_rooms_map
        )
        if result:
            scored.append(result)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:limit]


def rank_by_department(docs: list[dict], department: str) -> list[dict]:
    """Attach a fixed department score to each doc — no sorting needed."""
    return [
        {
            "id":                  d["_id"],
            "name":                d["name"],
            "registration_number": d["registration_number"],
            "department":          d.get("department", ""),
            "profile_picture":     d.get("profile_picture", ""),
            "is_alumni":           d.get("is_alumni", False),
            "year_of_study":       d.get("year_of_study"),
            "skills":              d.get("skills", []),
            "mutual_connections":  0,
            "match_score":         W_DEPARTMENT,
            "match_reasons":       [f"Same department: {department}"],
        }
        for d in docs
    ]


def rank_by_skills(
    docs:     list[dict],
    my_set:   set[str],
    limit:    int
) -> list[dict]:
    """Score by skill overlap count and return top `limit`."""
    results = []
    for d in docs:
        their_set = set(s.lower() for s in d.get("skills", []))
        common    = my_set & their_set
        if not common:
            continue
        readable = ", ".join(s.title() for s in list(common)[:3])
        results.append({
            "id":                  d["_id"],
            "name":                d["name"],
            "registration_number": d["registration_number"],
            "department":          d.get("department", ""),
            "profile_picture":     d.get("profile_picture", ""),
            "is_alumni":           d.get("is_alumni", False),
            "year_of_study":       d.get("year_of_study"),
            "skills":              d.get("skills", []),
            "mutual_connections":  0,
            "match_score":         min(len(common) * W_SKILL, W_SKILL_CAP),
            "match_reasons":       [
                f"{len(common)} shared skill"
                f"{'s' if len(common) > 1 else ''}: {readable}"
            ],
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:limit]