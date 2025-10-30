from fastapi import APIRouter, Depends, HTTPException, status
from app.models import UserUpdate, UserResponse
from app.utils.dependencies import get_current_active_user
from app.database import get_users_collection
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_active_user)):
    return UserResponse(
        id=current_user["_id"],
        name=current_user["name"],
        registration_number=current_user["registration_number"],
        email=current_user["email"],
        department=current_user["department"],
        year_of_study=current_user.get("year_of_study"),
        is_alumni=current_user.get("is_alumni", False),
        bio=current_user.get("bio", ""),
        location=current_user.get("location", "Burla, Odisha"),
        profile_picture=current_user.get("profile_picture", ""),
        linkedin_url=current_user.get("linkedin_url"),
        github_url=current_user.get("github_url"),
        skills=current_user.get("skills", []),
        connections=len(current_user.get("connections", [])),
        joined_date=current_user.get("created_at", datetime.utcnow())
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    users_collection = await get_users_collection()
    update_data = user_update.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        
        await users_collection.update_one(
            {"_id": ObjectId(current_user["_id"])},
            {"$set": update_data}
        )
        
        updated_user = await users_collection.find_one({"_id": ObjectId(current_user["_id"])})
        updated_user["_id"] = str(updated_user["_id"])
        
        return UserResponse(
            id=updated_user["_id"],
            name=updated_user["name"],
            registration_number=updated_user["registration_number"],
            email=updated_user["email"],
            department=updated_user["department"],
            year_of_study=updated_user.get("year_of_study"),
            is_alumni=updated_user.get("is_alumni", False),
            bio=updated_user.get("bio", ""),
            location=updated_user.get("location", "Burla, Odisha"),
            profile_picture=updated_user.get("profile_picture", ""),
            linkedin_url=updated_user.get("linkedin_url"),
            github_url=updated_user.get("github_url"),
            skills=updated_user.get("skills", []),
            connections=len(updated_user.get("connections", [])),
            joined_date=updated_user.get("created_at", datetime.utcnow())
        )
    
    return await get_current_user_profile(current_user)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str):
    users_collection = await get_users_collection()
    
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        registration_number=user["registration_number"],
        email=user["email"],
        department=user["department"],
        year_of_study=user.get("year_of_study"),
        is_alumni=user.get("is_alumni", False),
        bio=user.get("bio", ""),
        location=user.get("location", "Burla, Odisha"),
        profile_picture=user.get("profile_picture", ""),
        linkedin_url=user.get("linkedin_url"),
        github_url=user.get("github_url"),
        skills=user.get("skills", []),
        connections=len(user.get("connections", [])),
        joined_date=user.get("created_at", datetime.utcnow())
    )

@router.get("/", response_model=List[UserResponse])
async def search_users(
    query: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    users_collection = await get_users_collection()
    filters = {}
    
    if query:
        filters["$or"] = [
            {"name": {"$regex": query, "$options": "i"}},
            {"registration_number": {"$regex": query, "$options": "i"}}
        ]
    if department:
        filters["department"] = department
    
    cursor = users_collection.find(filters).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return [
        UserResponse(
            id=str(user["_id"]),
            name=user["name"],
            registration_number=user["registration_number"],
            email=user["email"],
            department=user["department"],
            year_of_study=user.get("year_of_study"),
            is_alumni=user.get("is_alumni", False),
            bio=user.get("bio", ""),
            location=user.get("location", "Burla, Odisha"),
            profile_picture=user.get("profile_picture", ""),
            linkedin_url=user.get("linkedin_url"),
            github_url=user.get("github_url"),
            skills=user.get("skills", []),
            connections=len(user.get("connections", [])),
            joined_date=user.get("created_at", datetime.utcnow())
        )
        for user in users
    ]

@router.post("/connect/{user_id}")
async def connect_with_user(
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    users_collection = await get_users_collection()
    
    if user_id == current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot connect with yourself"
        )
    
    try:
        target_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    current_connections = current_user.get("connections", [])
    if user_id in current_connections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already connected with this user"
        )
    
    await users_collection.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$push": {"connections": user_id}}
    )
    
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$push": {"connections": current_user["_id"]}}
    )
    
    return {"message": "Connected successfully"}

@router.delete("/connect/{user_id}")
async def disconnect_user(
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    users_collection = await get_users_collection()
    current_connections = current_user.get("connections", [])
    if user_id not in current_connections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not connected with this user"
        )
    await users_collection.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$pull": {"connections": user_id}}
    )
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"connections": current_user["_id"]}}
    )
    
    return {"message": "Disconnected successfully"}