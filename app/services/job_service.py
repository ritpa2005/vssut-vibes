from datetime import datetime
from typing import Optional
from bson.errors import InvalidId
from fastapi import UploadFile

from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    AlreadyExistsException,
)
from app.repositories import job_repo
from app.schemas.job import JobResponse, JobUpdate, job_to_response
from app.services.cloudinary_service import upload_job_logo


async def create(
    title:        str,
    company:      str,
    location:     str,
    job_type:     str,
    salary:       str,
    description:  str,
    requirements: str,
    deadline:     Optional[str],
    logo:         UploadFile | None,
    current_user: dict
) -> JobResponse:
    logo_url = await upload_job_logo(logo)

    job_dict = {
        "title":          title,
        "company":        company,
        "location":       location,
        "type":           job_type,
        "salary":         salary,
        "description":    description,
        "requirements":   requirements,
        "posted_by":      current_user["_id"],
        "posted_by_name": current_user["name"],
        "logo":           logo_url,
        "posted_date":    datetime.utcnow(),
        "deadline":       deadline,
        "is_active":      True,
        "applicants":     [],
        "views":          0,
    }

    inserted_id     = await job_repo.insert(job_dict)
    job_dict["_id"] = inserted_id
    return job_to_response(job_dict)

async def get_all(
    job_type:  Optional[str],
    location:  Optional[str],
    company:   Optional[str],
    search:    Optional[str],
    skip:      int,
    limit:     int
) -> list[JobResponse]:
    jobs = await job_repo.find_many(job_type, location, company, search, skip, limit)
    return [job_to_response(j) for j in jobs]

async def get_by_id(job_id: str) -> JobResponse:
    try:
        job = await job_repo.find_by_id(job_id)
    except InvalidId:
        raise BadRequestException("Invalid job ID format")

    if not job:
        raise NotFoundException("Job")

    await job_repo.increment_views(job_id)
    job["views"] = job.get("views", 0) + 1

    return job_to_response(job)

async def update(
    job_id:      str,
    job_update:  JobUpdate,
    current_user: dict
) -> JobResponse:
    try:
        job = await job_repo.find_by_id(job_id)
    except InvalidId:
        raise BadRequestException("Invalid job ID format")

    if not job:
        raise NotFoundException("Job")
    if job["posted_by"] != current_user["_id"]:
        raise ForbiddenException("You don't have permission to update this job")

    update_data = job_update.dict(exclude_unset=True)
    if not update_data:
        return job_to_response(job)

    updated = await job_repo.update_by_id(job_id, update_data)
    return job_to_response(updated)

async def delete(job_id: str, current_user: dict) -> dict:
    try:
        job = await job_repo.find_by_id(job_id)
    except InvalidId:
        raise BadRequestException("Invalid job ID format")

    if not job:
        raise NotFoundException("Job")
    if job["posted_by"] != current_user["_id"]:
        raise ForbiddenException("You don't have permission to delete this job")

    await job_repo.set_inactive(job_id)
    return {"message": "Job posting deactivated successfully"}


async def apply(job_id: str, current_user: dict) -> dict:
    try:
        job = await job_repo.find_by_id(job_id)
    except InvalidId:
        raise BadRequestException("Invalid job ID format")

    if not job:
        raise NotFoundException("Job")
    if not job.get("is_active", False):
        raise BadRequestException("This job posting is no longer active")
    if current_user["_id"] in job.get("applicants", []):
        raise AlreadyExistsException("You have already applied for this job")

    await job_repo.push_applicant(job_id, current_user["_id"])
    return {"message": "Application submitted successfully"}