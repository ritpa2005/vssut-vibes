from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from typing import List
from app.core.limiter import limiter
from app.schemas.post import PostUpdate, PostResponse, CommentCreate, CommentResponse
from app.core.dependencies import get_current_active_user
from app.services import post_service

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=List[PostResponse])
async def get_posts(
    limit:        int  = Query(20, ge=1, le=100),
    skip:         int  = Query(0,  ge=0),
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.get_feed(current_user, skip, limit)

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_post(
    request:      Request,
    content:      str        = Form(...),
    image:        UploadFile = File(None),
    current_user: dict       = Depends(get_current_active_user)
):
    return await post_service.create(content, image, current_user)


@router.get("/user/{user_id}", response_model=List[PostResponse])
async def get_user_posts(
    user_id:      str,
    limit:        int  = Query(20, ge=1, le=100),
    skip:         int  = Query(0,  ge=0),
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.get_by_author(user_id, current_user, skip, limit)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post_by_id(
    post_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.get_by_id(post_id, current_user)

@router.put("/{post_id}", response_model=PostResponse)
@limiter.limit("15/minute")
async def update_post(
    request:      Request,
    post_id:      str,
    post_update:  PostUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.update(
        post_id,
        post_update.dict(exclude_unset=True),
        current_user
    )

@router.delete("/{post_id}")
async def delete_post(
    post_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.delete(post_id, current_user)


@router.post("/{post_id}/like")
@limiter.limit("30/minute")
async def like_post(
    request:      Request,
    post_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.toggle_like(post_id, current_user)

@router.post("/{post_id}/comment", response_model=CommentResponse)
@limiter.limit("15/minute")
async def add_comment(
    request:      Request,
    post_id:      str,
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    return await post_service.add_comment(post_id, comment_data.content, current_user)

@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(post_id: str):
    return await post_service.get_comments(post_id)