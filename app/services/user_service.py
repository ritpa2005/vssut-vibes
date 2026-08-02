from typing import Optional
from bson.errors import InvalidId
from fastapi import UploadFile
from app.core.cache import cache, CacheKey

from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    AlreadyExistsException
)
from app.repositories import user_repo
from app.schemas.user import UserResponse, UserUpdate, user_to_response
from app.services import suggestion_service
from app.services.cloudinary_service import upload_profile_picture


async def get_me(current_user: dict) -> UserResponse:
    return user_to_response(current_user)

async def update_me(current_user: dict, user_update: UserUpdate) -> UserResponse:
    update_data = user_update.model_dump(exclude_unset=True)

    if not update_data:
        return user_to_response(current_user)
    
    if "skills" in update_data:
        await _invalidate_suggestions(current_user["_id"])

    updated = await user_repo.update_by_id(current_user["_id"], update_data)
    return user_to_response(updated)

async def update_profile_picture(current_user: dict, file: UploadFile) -> UserResponse:
    picture_url = await upload_profile_picture(file)
    updated     = await user_repo.update_by_id(current_user["_id"], {"profile_picture": picture_url})
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

    await _invalidate_suggestions(current_user["_id"])
    await _invalidate_suggestions(user_id)

    return {"message": "Connected successfully"}

async def disconnect(current_user: dict, user_id: str) -> dict:
    try:
        # validating ID format
        from bson import ObjectId
        ObjectId(user_id)
    except InvalidId:
        raise BadRequestException("Invalid user ID format")

    if user_id not in current_user.get("connections", []):
        raise BadRequestException("Not connected with this user")

    await user_repo.pull_connection(current_user["_id"], user_id)
    await user_repo.pull_connection(user_id, current_user["_id"])

    return {"message": "Disconnected successfully"}


async def get_suggestions(current_user: dict, limit: int):
    return await suggestion_service.get_suggestions(current_user, limit)
 
async def get_suggestions_by_department(current_user: dict, limit: int):
    return await suggestion_service.get_suggestions_by_department(current_user, limit)
 
async def get_suggestions_by_skills(current_user: dict, limit: int):
    return await suggestion_service.get_suggestions_by_skills(current_user, limit)

async def _invalidate_suggestions(user_id: str) -> None:
    await cache.delete(CacheKey.suggestions(user_id))
    await cache.delete(CacheKey.suggestions_dept(user_id))
    await cache.delete(CacheKey.suggestions_skills(user_id))