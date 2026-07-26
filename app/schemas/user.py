# app/schemas/user.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserUpdate(BaseModel):
    bio:             Optional[str]       = None
    location:        Optional[str]       = None
    linkedin_url:    Optional[str]       = None
    github_url:      Optional[str]       = None
    skills:          Optional[List[str]] = None
    profile_picture: Optional[str]       = None
    year_of_study:   Optional[str]       = None
    is_alumni:       Optional[bool]      = None


class UserResponse(BaseModel):
    id:                  str
    name:                str
    registration_number: str
    email:               EmailStr
    department:          str
    year_of_study:       Optional[str]       = None
    is_alumni:           bool
    bio:                 str
    location:            str
    profile_picture:     str
    linkedin_url:        Optional[str]       = None
    github_url:          Optional[str]       = None
    skills:              List[str]
    user_connections:    List[str]           = []   # raw connection IDs
    connections:         int                        # count
    joined_date:         datetime


def user_to_response(user: dict) -> UserResponse:
    """
    Single place that maps a raw MongoDB user document → UserResponse.
    Import and call this from the service layer only.
    """
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
        user_connections=user.get("connections", []),
        connections=len(user.get("connections", [])),
        joined_date=user.get("created_at", datetime.utcnow())
    )