from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from typing import List, Optional

from app.schemas.job import JobUpdate, JobResponse
from app.core.dependencies import get_current_active_user
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["Jobs & Internships"])


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    title:        str        = Form(...),
    company:      str        = Form(...),
    location:     str        = Form(""),
    type:         str        = Form(...),
    salary:       str        = Form(""),
    description:  str        = Form(...),
    requirements: str        = Form(...),
    deadline:     str        = Form(None),
    logo:         UploadFile = File(None),
    current_user: dict       = Depends(get_current_active_user)
):
    return await job_service.create(
        title=title,
        company=company,
        location=location,
        job_type=type,
        salary=salary,
        description=description,
        requirements=requirements,
        deadline=deadline,
        logo=logo,
        current_user=current_user
    )


@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    job_type:  Optional[str] = Query(None, description="Internship, Full-time, Part-time, Contract"),
    location:  Optional[str] = None,
    company:   Optional[str] = None,
    search:    Optional[str] = None,
    limit:     int           = Query(20, ge=1, le=100),
    skip:      int           = Query(0,  ge=0)
):
    return await job_service.get_all(job_type, location, company, search, skip, limit)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str):
    return await job_service.get_by_id(job_id)


@router.post("/{job_id}/apply")
async def apply_for_job(
    job_id:       str,
    current_user: dict = Depends(get_current_active_user)
):
    return await job_service.apply(job_id, current_user)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id:       str,
    job_update:   JobUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    return await job_service.update(job_id, job_update, current_user)


@router.delete("/{job_id}")
async def delete_job(
    job_id:       str,
    current_user: dict = Depends(get_current_active_user)
):
    return await job_service.delete(job_id, current_user)