from fastapi import APIRouter, HTTPException, status, Depends, Form, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from app.models import UserCreate
from app.database import get_users_collection
from app.utils.security import verify_password, get_password_hash, create_access_token
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
import os

router = APIRouter(prefix="/auth", tags=["Authentication"])

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    registration_number: str = Form(...),
    department: str = Form(...),
    year_of_study: str = Form(...),
    location: str = Form("Burla, Odisha"),
    bio: str = Form(""),
    linkedin_url: str = Form(None),
    github_url: str = Form(None),
    skills: str = Form(""),
    profile_picture: UploadFile = File(None),
):
    users_collection = await get_users_collection()
    existing_user = await users_collection.find_one({
        "$or": [
            {"email": email},
            {"registration_number": registration_number}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or registration number already exists"
        )
    
    profile_pic_url = "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg"

    if profile_picture:
        os.makedirs("media/profile_pics", exist_ok=True)
        file_name = f"user_{datetime.utcnow().timestamp()}.jpg"
        file_path = f"media/profile_pics/{file_name}"

        with open(file_path, "wb") as f:
            f.write(await profile_picture.read())

        profile_pic_url = f"http://127.0.0.1:8000/media/profile_pics/{file_name}"

    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    
    user_dict = {
        "name": name,
        "registration_number": registration_number,
        "email": email,
        "password": get_password_hash(password),
        "department": department,
        "year_of_study": year_of_study,
        "is_alumni": False,
        "bio": bio,
        "location": location,
        "profile_picture": profile_pic_url or "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&w=400",
        "linkedin_url": linkedin_url,
        "github_url": github_url,
        "skills": skills_list,
        "connections": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await users_collection.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(data={"sub": str(user_id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": user_dict["name"],
            "email": user_dict["email"],
            "registration_number": user_dict["registration_number"],
            "department": user_dict["department"],
            "year_of_study": user_dict["year_of_study"],
            "is_alumni": user_dict["is_alumni"],
            "bio": user_dict["bio"],
            "location": user_dict["location"],
            "profile_picture": user_dict["profile_picture"],
            "linkedin_url": user_dict["linkedin_url"],
            "github_url": user_dict["github_url"],
            "skills": user_dict["skills"],
            "connections": 0,
            "joined_date": user_dict["created_at"]
        }
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "registration_number": user["registration_number"],
            "profile_picture": user["profile_picture"]
        }
    }

@router.post("/login/json", response_model=Token)
async def login_json(login_data: LoginRequest):
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"email": login_data.email})
    
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "registration_number": user["registration_number"],
            "department": user["department"],
            "year_of_study": user.get("year_of_study"),
            "is_alumni": user.get("is_alumni", False),
            "bio": user.get("bio", ""),
            "location": user.get("location", "Burla, Odisha"),
            "profile_picture": user.get("profile_picture"),
            "linkedin_url": user.get("linkedin_url"),
            "github_url": user.get("github_url"),
            "skills": user.get("skills", []),
            "connections": len(user.get("connections", [])),
            "joined_date": user.get("created_at")
        }
    }