from fastapi import APIRouter, status, Form, File, UploadFile, Request, Response
from app.core.limiter import limiter
from app.schemas.auth import Token, LoginRequest
from app.services.auth_service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request:             Request,
    response:            Response,
    name:                str        = Form(...),
    email:               str        = Form(...),
    password:            str        = Form(...),
    registration_number: str        = Form(...),
    department:          str        = Form(...),
    year_of_study:       str        = Form(...),
    location:            str        = Form("Burla, Odisha"),
    bio:                 str        = Form(""),
    linkedin_url:        str        = Form(None),
    github_url:          str        = Form(None),
    skills:              str        = Form(""),
    profile_picture:     UploadFile = File(None),
):
    return await register_user(
        name=name,
        email=email,
        password=password,
        registration_number=registration_number,
        department=department,
        year_of_study=year_of_study,
        location=location,
        bio=bio,
        linkedin_url=linkedin_url,
        github_url=github_url,
        skills_raw=skills,
        profile_picture=profile_picture,
    )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, response: Response, login_data: LoginRequest):
    return await login_user(
        email=login_data.email,
        password=login_data.password,
    )