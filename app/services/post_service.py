from datetime import datetime
from bson.errors import InvalidId
from fastapi import UploadFile

from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    ModerationException
)
from app.repositories import post_repo
from app.schemas.post import (
    PostResponse, CommentResponse,
    post_to_response, comment_to_response
)
from app.services.moderation_service import moderate_content
from app.services.cloudinary_service import upload_post_image


async def create(
    content:      str,
    image:        UploadFile | None,
    current_user: dict
) -> PostResponse:
    image_url = await upload_post_image(image)

    mod = await moderate_content(text=content, image_url=image_url)
    if mod.flagged:
        raise ModerationException(reason=mod.reason, category=mod.category)

    post_dict = {
        "author_id":                  current_user["_id"],
        "author_name":                current_user["name"],
        "author_registration_number": current_user["registration_number"],
        "author_department":          current_user["department"],
        "author_profile_picture":     current_user.get("profile_picture", ""),
        "content":                    content,
        "image":                      image_url,
        "likes":                      [],
        "comments":                   [],
        "created_at":                 datetime.utcnow(),
        "updated_at":                 datetime.utcnow(),
    }

    inserted_id      = await post_repo.insert(post_dict)
    post_dict["_id"] = inserted_id

    return post_to_response(post_dict, current_user["_id"])

async def get_feed(current_user: dict, skip: int, limit: int) -> list[PostResponse]:
    posts = await post_repo.find_feed(skip, limit)
    return [post_to_response(p, current_user["_id"]) for p in posts]

async def get_by_id(post_id: str, current_user: dict) -> PostResponse:
    try:
        post = await post_repo.find_by_id(post_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid post ID format")

    if not post:
        raise NotFoundException("Post")

    return post_to_response(post, current_user["_id"])

async def get_by_author(
    author_id:    str,
    current_user: dict,
    skip:         int,
    limit:        int
) -> list[PostResponse]:
    posts = await post_repo.find_by_author(author_id, skip, limit)
    return [post_to_response(p, current_user["_id"]) for p in posts]

async def update(post_id: str, update_data: dict, current_user: dict) -> PostResponse:
    try:
        post = await post_repo.find_by_id(post_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid post ID format")

    if not post:
        raise NotFoundException("Post")

    if post["author_id"] != current_user["_id"]:
        raise ForbiddenException("You don't have permission to update this post")

    if not update_data:
        return post_to_response(post, current_user["_id"])

    updated = await post_repo.update_by_id(post_id, update_data)
    return post_to_response(updated, current_user["_id"])

async def delete(post_id: str, current_user: dict) -> dict:
    try:
        post = await post_repo.find_by_id(post_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid post ID format")

    if not post:
        raise NotFoundException("Post")

    if post["author_id"] != current_user["_id"]:
        raise ForbiddenException("You don't have permission to delete this post")

    await post_repo.delete_by_id(post_id)
    return {"message": "Post deleted successfully"}


async def toggle_like(post_id: str, current_user: dict) -> dict:
    try:
        post = await post_repo.find_by_id(post_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid post ID format")

    if not post:
        raise NotFoundException("Post")

    likes     = post.get("likes", [])
    user_id   = current_user["_id"]
    already   = user_id in likes

    if already:
        await post_repo.pull_like(post_id, user_id)
        return {"message": "Post unliked", "likes_count": len(likes) - 1}
    else:
        await post_repo.push_like(post_id, user_id)
        return {"message": "Post liked",   "likes_count": len(likes) + 1}


async def add_comment(
    post_id:      str,
    content:      str,
    current_user: dict
) -> CommentResponse:
    try:
        post = await post_repo.find_by_id(post_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid post ID format")

    if not post:
        raise NotFoundException("Post")

    comment = {
        "author_id":      current_user["_id"],
        "author_name":    current_user["name"],
        "author_picture": current_user.get("profile_picture", ""),
        "content":        content,
        "created_at":     datetime.utcnow(),
    }

    await post_repo.push_comment(post_id, comment)
    return comment_to_response(comment)

async def get_comments(post_id: str) -> list[CommentResponse]:
    try:
        post = await post_repo.find_by_id(post_id)
    except (InvalidId, Exception):
        raise BadRequestException("Invalid post ID format")

    if not post:
        raise NotFoundException("Post")

    return [comment_to_response(c) for c in post.get("comments", [])]