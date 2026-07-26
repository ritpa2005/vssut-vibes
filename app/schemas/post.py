# app/schemas/post.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PostCreate(BaseModel):
    content: str


class PostUpdate(BaseModel):
    content: Optional[str] = None


class CommentCreate(BaseModel):
    content: str


class AuthorInfo(BaseModel):
    name:                str
    registration_number: str
    department:          str
    profile_picture:     str


class PostResponse(BaseModel):
    id:        str
    author:    AuthorInfo
    content:   str
    image:     Optional[str]
    likes:     int
    comments:  int
    timestamp: str
    is_liked:  bool = False


class CommentResponse(BaseModel):
    author_name:    str
    author_picture: str
    content:        str
    created_at:     datetime


# ── Mapping helpers ───────────────────────────────────────────────────────────

def post_to_response(post: dict, current_user_id: str) -> PostResponse:
    """
    Single place that maps a raw MongoDB post document → PostResponse.
    Import and call this from service layer only — never build PostResponse manually.
    """
    from app.utils.formatters import format_time_ago

    return PostResponse(
        id=str(post["_id"]),
        author=AuthorInfo(
            name=post["author_name"],
            registration_number=post["author_registration_number"],
            department=post["author_department"],
            profile_picture=post["author_profile_picture"]
        ),
        content=post["content"],
        image=post.get("image"),
        likes=len(post.get("likes", [])),
        comments=len(post.get("comments", [])),
        timestamp=format_time_ago(post["created_at"]),
        is_liked=current_user_id in post.get("likes", [])
    )


def comment_to_response(comment: dict) -> CommentResponse:
    return CommentResponse(
        author_name=comment["author_name"],
        author_picture=comment["author_picture"],
        content=comment["content"],
        created_at=comment["created_at"]
    )