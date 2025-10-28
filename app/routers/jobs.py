from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models import JobCreate, JobUpdate, JobResponse
from app.utils.dependencies import get_current_active_user
from app.database import get_jobs_collection
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter(prefix="/jobs", tags=["Jobs & Internships"])


def format_time_ago(dt: datetime) -> str:
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 30:
        return f"{diff.days // 30} month{'s' if diff.days // 30 > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new job/internship posting"""
    jobs_collection = await get_jobs_collection()
    
    job_dict = {
        "title": job_data.title,
        "company": job_data.company,
        "location": job_data.location,
        "type": job_data.type,
        "salary": job_data.salary,
        "description": job_data.description,
        "requirements": job_data.requirements,
        "posted_by": current_user["_id"],
        "posted_by_name": current_user["name"],
        "logo": job_data.logo or "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg?auto=compress&cs=tinysrgb&w=400",
        "posted_date": datetime.utcnow(),
        "deadline": job_data.deadline,
        "is_active": True,
        "applicants": [],
        "views": 0
    }
    
    result = await jobs_collection.insert_one(job_dict)
    job_dict["_id"] = str(result.inserted_id)
    
    return JobResponse(
        id=job_dict["_id"],
        title=job_dict["title"],
        company=job_dict["company"],
        location=job_dict["location"],
        type=job_dict["type"],
        salary=job_dict["salary"],
        description=job_dict["description"],
        requirements=job_dict["requirements"],
        posted_by_name=job_dict["posted_by_name"],
        logo=job_dict["logo"],
        posted_date=format_time_ago(job_dict["posted_date"]),
        deadline=job_dict["deadline"],
        is_active=job_dict["is_active"],
        applicants_count=len(job_dict["applicants"]),
        views=job_dict["views"]
    )


@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    job_type: Optional[str] = Query(None, description="Filter by type: Internship, Full-time, Part-time, Contract"),
    location: Optional[str] = None,
    company: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """Get all jobs/internships with filters"""
    jobs_collection = await get_jobs_collection()
    filters = {"is_active": True}
    
    if job_type:
        filters["type"] = job_type
    
    if location:
        filters["location"] = {"$regex": location, "$options": "i"}
    
    if company:
        filters["company"] = {"$regex": company, "$options": "i"}
    
    if search:
        filters["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = jobs_collection.find(filters).sort("posted_date", -1).skip(skip).limit(limit)
    jobs = await cursor.to_list(length=limit)
    
    return [
        JobResponse(
            id=str(job["_id"]),
            title=job["title"],
            company=job["company"],
            location=job["location"],
            type=job["type"],
            salary=job.get("salary"),
            description=job["description"],
            requirements=job["requirements"],
            posted_by_name=job["posted_by_name"],
            logo=job["logo"],
            posted_date=format_time_ago(job["posted_date"]),
            deadline=job.get("deadline"),
            is_active=job["is_active"],
            applicants_count=len(job.get("applicants", [])),
            views=job.get("views", 0)
        )
        for job in jobs
    ]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str):
    """Get job details by ID"""
    jobs_collection = await get_jobs_collection()
    
    try:
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Increment views
    await jobs_collection.update_one(
        {"_id": ObjectId(job_id)},
        {"$inc": {"views": 1}}
    )
    job["views"] = job.get("views", 0) + 1
    
    return JobResponse(
        id=str(job["_id"]),
        title=job["title"],
        company=job["company"],
        location=job["location"],
        type=job["type"],
        salary=job.get("salary"),
        description=job["description"],
        requirements=job["requirements"],
        posted_by_name=job["posted_by_name"],
        logo=job["logo"],
        posted_date=format_time_ago(job["posted_date"]),
        deadline=job.get("deadline"),
        is_active=job["is_active"],
        applicants_count=len(job.get("applicants", [])),
        views=job["views"]
    )


@router.post("/{job_id}/apply")
async def apply_for_job(
    job_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Apply for a job/internship"""
    jobs_collection = await get_jobs_collection()
    
    try:
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if not job.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job posting is no longer active"
        )
    
    if current_user["_id"] in job.get("applicants", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied for this job"
        )
    
    await jobs_collection.update_one(
        {"_id": ObjectId(job_id)},
        {"$push": {"applicants": current_user["_id"]}}
    )
    
    return {"message": "Application submitted successfully"}


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update a job posting"""
    jobs_collection = await get_jobs_collection()
    
    try:
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job["posted_by"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this job"
        )
    
    update_data = job_update.dict(exclude_unset=True)
    if update_data:
        await jobs_collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        # Get updated job
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
    
    return JobResponse(
        id=str(job["_id"]),
        title=job["title"],
        company=job["company"],
        location=job["location"],
        type=job["type"],
        salary=job.get("salary"),
        description=job["description"],
        requirements=job["requirements"],
        posted_by_name=job["posted_by_name"],
        logo=job["logo"],
        posted_date=format_time_ago(job["posted_date"]),
        deadline=job.get("deadline"),
        is_active=job["is_active"],
        applicants_count=len(job.get("applicants", [])),
        views=job.get("views", 0)
    )


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete/deactivate a job posting"""
    jobs_collection = get_jobs_collection()
    
    try:
        job = await jobs_collection.find_one({"_id": ObjectId(job_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job["posted_by"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this job"
        )
    
    await jobs_collection.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Job posting deactivated successfully"}