from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from typing import List, Optional
from app.core.limiter import limiter
from app.schemas.user import UserUpdate, UserResponse
from app.schemas.suggestion import SuggestionsResponse
from app.core.dependencies import get_current_active_user
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_active_user)
):
    return await user_service.get_me(current_user)

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update:  UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    return await user_service.update_me(current_user, user_update)

@router.patch("/me/picture", response_model=UserResponse)
@limiter.limit("5/minute")
async def update_profile_picture(
    request:      Request,
    file:         UploadFile = File(...),
    current_user: dict       = Depends(get_current_active_user)
):
    return await user_service.update_profile_picture(current_user, file)


@router.get("/suggestions", response_model=SuggestionsResponse)
@limiter.limit("10/minute")
async def suggest_connections(
    request:      Request,
    limit:        int  = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user)
):
    results = await user_service.get_suggestions(current_user, limit)
    return SuggestionsResponse(suggestions=results, total=len(results))

@router.get("/suggestions/department", response_model=SuggestionsResponse)
@limiter.limit("10/minute")
async def suggest_by_department(
    request:      Request,
    limit:        int  = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user)
):
    results = await user_service.get_suggestions_by_department(current_user, limit)
    return SuggestionsResponse(suggestions=results, total=len(results))

@router.get("/suggestions/skills", response_model=SuggestionsResponse)
@limiter.limit("10/minute")
async def suggest_by_skills(
    request:      Request,
    limit:        int  = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_active_user)
):
    results = await user_service.get_suggestions_by_skills(current_user, limit)
    return SuggestionsResponse(suggestions=results, total=len(results))


@router.get("/", response_model=List[UserResponse])
async def search_users(
    query:      Optional[str] = None,
    department: Optional[str] = None,
    limit:      int           = Query(20, ge=1, le=100),
    skip:       int           = Query(0,  ge=0)
):
    return await user_service.search(query, department, skip, limit)


@router.post("/connect/{user_id}")
@limiter.limit("20/minute")
async def connect_with_user(
    request:      Request,
    user_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    return await user_service.connect(current_user, user_id)

@router.delete("/connect/{user_id}")
async def disconnect_user(
    user_id:      str,
    current_user: dict = Depends(get_current_active_user)
):
    return await user_service.disconnect(current_user, user_id)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str):
    return await user_service.get_by_id(user_id)