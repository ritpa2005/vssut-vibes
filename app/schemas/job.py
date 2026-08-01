from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class JobInDB(BaseModel):
    id:             str
    title:          str
    company:        str
    location:       str
    type:           str
    salary:         Optional[str]      = None
    description:    str
    requirements:   str
    posted_by:      str
    posted_by_name: str
    logo:           str
    posted_date:    datetime
    deadline:       Optional[datetime] = None
    is_active:      bool               = True
    applicants:     List[str]          = []
    views:          int                = 0
 
    class Config:
        populate_by_name = True

class JobUpdate(BaseModel):
    title:        Optional[str]      = None
    company:      Optional[str]      = None
    location:     Optional[str]      = None
    type:         Optional[str]      = None
    salary:       Optional[str]      = None
    description:  Optional[str]      = None
    requirements: Optional[str]      = None
    logo:         Optional[str]      = None
    deadline:     Optional[datetime] = None
    is_active:    Optional[bool]     = None

class JobResponse(BaseModel):
    id:              str
    title:           str
    company:         str
    location:        str
    type:            str
    salary:          Optional[str]
    description:     str
    requirements:    str
    posted_by_name:  str
    logo:            str
    posted_date:     str
    deadline:        Optional[str]
    is_active:       bool
    applicants_count: int
    views:           int


def job_to_response(job: dict) -> JobResponse:
    from app.utils.formatters import format_time_ago

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