from typing import Optional
from bson.errors import InvalidId

from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    AlreadyExistsException
)
from app.repositories import user_repo
from app.schemas.user import UserResponse, UserUpdate, user_to_response


# ── Profile ───────────────────────────────────────────────────────────────────

async def get_me(current_user: dict) -> UserResponse:
    return user_to_response(current_user)


async def update_me(current_user: dict, user_update: UserUpdate) -> UserResponse:
    update_data = user_update.dict(exclude_unset=True)

    if not update_data:
        return user_to_response(current_user)

    updated = await user_repo.update_by_id(current_user["_id"], update_data)
    return user_to_response(updated)


async def get_by_id(user_id: str) -> UserResponse:
    try:
        user = await user_repo.find_by_id(user_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid user ID format")

    if not user:
        raise NotFoundException("User")

    return user_to_response(user)


async def search(
    query: Optional[str],
    department: Optional[str],
    skip: int,
    limit: int
) -> list[UserResponse]:
    users = await user_repo.find_many(query, department, skip, limit)
    return [user_to_response(u) for u in users]


# ── Connections ───────────────────────────────────────────────────────────────

async def connect(current_user: dict, user_id: str) -> dict:
    if user_id == current_user["_id"]:
        raise BadRequestException("Cannot connect with yourself")

    try:
        target = await user_repo.find_by_id(user_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid user ID format")

    if not target:
        raise NotFoundException("User")

    if user_id in current_user.get("connections", []):
        raise AlreadyExistsException("Already connected with this user")

    await user_repo.push_connection(current_user["_id"], user_id)
    await user_repo.push_connection(user_id, current_user["_id"])

    return {"message": "Connected successfully"}


async def disconnect(current_user: dict, user_id: str) -> dict:
    try:
        # validate ID format even if we don't need the document
        from bson import ObjectId
        ObjectId(user_id)
    except InvalidId:
        raise BadRequestException("Invalid user ID format")

    if user_id not in current_user.get("connections", []):
        raise BadRequestException("Not connected with this user")

    await user_repo.pull_connection(current_user["_id"], user_id)
    await user_repo.pull_connection(user_id, current_user["_id"])

    return {"message": "Disconnected successfully"}