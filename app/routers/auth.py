from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.models import UserCreate
from app.database import get_users_collection
from app.utils.security import verify_password, get_password_hash, create_access_token
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    users_collection = await get_users_collection()
    
    # Check if user already exists
    existing_user = await users_collection.find_one({
        "$or": [
            {"email": user_data.email},
            {"registration_number": user_data.registration_number}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or registration number already exists"
        )
    
    # Create new user document
    user_dict = {
        "name": user_data.name,
        "registration_number": user_data.registration_number,
        "email": user_data.email,
        "password": get_password_hash(user_data.password),
        "department": user_data.department,
        "year_of_study": user_data.year_of_study,
        "is_alumni": False,
        "bio": "",
        "location": "Burla, Odisha",
        "profile_picture": "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&w=400",
        "linkedin_url": None,
        "github_url": None,
        "skills": [],
        "connections": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await users_collection.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    # Create access token
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "registration_number": user_data.registration_number,
            "profile_picture": user_dict["profile_picture"]
        }
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    users_collection = await get_users_collection()
    
    # Find user by email (username field contains email)
    user = await users_collection.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
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
    
    # Find user by email
    user = await users_collection.find_one({"email": login_data.email})
    
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
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