from datetime import datetime
from fastapi import UploadFile

from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import UnauthorizedException, AlreadyExistsException
from app.repositories.auth_repo import (
    find_by_email,
    find_by_email_or_registration,
    create_user
)
from app.services.cloudinary_service import upload_profile_picture

async def register_user(
    name: str,
    email: str,
    password: str,
    registration_number: str,
    department: str,
    year_of_study: str,
    location: str,
    bio: str,
    linkedin_url: str | None,
    github_url: str | None,
    skills_raw: str,
    profile_picture: UploadFile | None,
) -> dict:
    """
    Validate uniqueness, hash password, persist user, return token payload.
    Raises AlreadyExistsException if email or reg number is taken.
    """
    existing = await find_by_email_or_registration(email, registration_number)
    if existing:
        raise AlreadyExistsException(
            "User with this email or registration number already exists"
        )

    profile_pic_url = await upload_profile_picture(profile_picture)
    skills_list     = [s.strip() for s in skills_raw.split(",") if s.strip()]

    user_dict = {
        "name":                name,
        "registration_number": registration_number,
        "email":               email,
        "password":            get_password_hash(password),
        "department":          department,
        "year_of_study":       year_of_study,
        "is_alumni":           False,
        "bio":                 bio,
        "location":            location,
        "profile_picture":     profile_pic_url,
        "linkedin_url":        linkedin_url,
        "github_url":          github_url,
        "skills":              skills_list,
        "connections":         [],
        "created_at":          datetime.utcnow(),
        "updated_at":          datetime.utcnow(),
    }

    user_id      = await create_user(user_dict)
    access_token = create_access_token(data={"sub": user_id})

    return {
        "access_token": access_token,
        "token_type":   "bearer",
        "user": {
            "id":                  user_id,
            "name":                user_dict["name"],
            "email":               user_dict["email"],
            "registration_number": user_dict["registration_number"],
            "department":          user_dict["department"],
            "year_of_study":       user_dict["year_of_study"],
            "is_alumni":           user_dict["is_alumni"],
            "bio":                 user_dict["bio"],
            "location":            user_dict["location"],
            "profile_picture":     user_dict["profile_picture"],
            "linkedin_url":        user_dict["linkedin_url"],
            "github_url":          user_dict["github_url"],
            "skills":              user_dict["skills"],
            "connections":         0,
            "joined_date":         user_dict["created_at"],
        }
    }

async def login_user(email: str, password: str) -> dict:
    """
    Verify credentials and return token payload.
    Raises UnauthorizedException if email not found or password wrong.
    """
    user = await find_by_email(email)

    if not user or not verify_password(password, user["password"]):
        raise UnauthorizedException("Incorrect email or password")

    access_token = create_access_token(data={"sub": str(user["_id"])})

    return {
        "access_token": access_token,
        "token_type":   "bearer",
        "user": {
            "id":                  str(user["_id"]),
            "name":                user["name"],
            "email":               user["email"],
            "registration_number": user["registration_number"],
            "department":          user["department"],
            "year_of_study":       user.get("year_of_study"),
            "is_alumni":           user.get("is_alumni", False),
            "bio":                 user.get("bio", ""),
            "location":            user.get("location", "Burla, Odisha"),
            "profile_picture":     user.get("profile_picture"),
            "linkedin_url":        user.get("linkedin_url"),
            "github_url":          user.get("github_url"),
            "skills":              user.get("skills", []),
            "connections":         len(user.get("connections", [])),
            "joined_date":         user.get("created_at"),
        }
    }