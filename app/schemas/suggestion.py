from pydantic import BaseModel
from typing import Optional, List


class SuggestedUser(BaseModel):
    id:                  str
    name:                str
    registration_number: str
    department:          str
    profile_picture:     str
    is_alumni:           bool
    year_of_study:       Optional[str]
    skills:              List[str]
    mutual_connections:  int
    match_score:         int
    match_reasons:       List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Priya Patel",
                "registration_number": "2020UEC5678",
                "department": "Computer Science & Engineering",
                "profile_picture": "https://i.pravatar.cc/400?img=10",
                "is_alumni": False,
                "year_of_study": "3rd Year",
                "skills": ["Python", "React", "ML"],
                "mutual_connections": 3,
                "match_score": 70,
                "match_reasons": [
                    "Same department: Computer Science & Engineering",
                    "3 shared skills: Python, React, ML"
                ]
            }
        }


class SuggestionsResponse(BaseModel):
    suggestions: List[SuggestedUser]
    total:       int