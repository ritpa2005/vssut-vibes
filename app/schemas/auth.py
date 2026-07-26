# app/schemas/auth.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "rahul.sharma@vssut.ac.in",
                "password": "securepassword123"
            }
        }


class AuthUserResponse(BaseModel):
    """User object returned inside the token response."""
    id: str
    name: str
    email: str
    registration_number: str
    department: Optional[str] = None
    year_of_study: Optional[str] = None
    is_alumni: bool = False
    bio: str = ""
    location: str = "Burla, Odisha"
    profile_picture: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    skills: List[str] = []
    connections: int = 0
    joined_date: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: AuthUserResponse