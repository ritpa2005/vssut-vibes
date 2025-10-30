from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    department: str

class UserCreate(BaseModel):
    name: str
    registration_number: str
    email: EmailStr
    password: str
    department: str
    year_of_study: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rahul Sharma",
                "registration_number": "2021UCS1234",
                "email": "rahul.sharma@vssut.ac.in",
                "password": "securepassword123",
                "department": "Computer Science & Engineering",
                "year_of_study": "3rd Year"
            }
        }

class UserUpdate(BaseModel):
    bio: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    skills: Optional[List[str]] = None
    profile_picture: Optional[str] = None
    year_of_study: Optional[str] = None
    is_alumni: Optional[bool] = None

class UserInDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    registration_number: str
    email: EmailStr
    password: str
    department: str
    year_of_study: Optional[str] = None
    is_alumni: bool = False
    bio: str = ""
    location: str = "Burla, Odisha"
    profile_picture: str = "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&w=400"
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    skills: List[str] = []
    connections: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

class UserResponse(BaseModel):
    id: str
    name: str
    registration_number: str
    email: EmailStr
    department: str
    year_of_study: Optional[str] = None
    is_alumni: bool
    bio: str
    location: str
    profile_picture: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    skills: List[str]
    connections: int
    joined_date: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Rahul Sharma",
                "registration_number": "2021UCS1234",
                "email": "rahul.sharma@vssut.ac.in",
                "department": "Computer Science & Engineering",
                "year_of_study": "3rd Year",
                "is_alumni": False,
                "bio": "Passionate about web development",
                "location": "Burla, Odisha",
                "profile_picture": "https://example.com/pic.jpg",
                "linkedin_url": "https://linkedin.com/in/rahulsharma",
                "github_url": "https://github.com/rahulsharma",
                "skills": ["React", "Python", "Machine Learning"],
                "connections": 156,
                "joined_date": "2021-08-15T10:30:00"
            }
        }

class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    type: str 
    salary: Optional[str] = None
    description: str
    requirements: str
    logo: Optional[str] = None
    deadline: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Software Development Intern",
                "company": "Google",
                "location": "Bangalore, Karnataka",
                "type": "Internship",
                "salary": "₹50,000 - ₹80,000/month",
                "description": "Join our team to work on cutting-edge technology.",
                "requirements": "Strong coding skills in Java/Python",
                "logo": "https://example.com/logo.jpg",
                "deadline": "2025-12-31T23:59:59"
            }
        }

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    logo: Optional[str] = None
    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None

class JobInDB(BaseModel):
    id: str = Field(alias="_id")
    title: str
    company: str
    location: str
    type: str
    salary: Optional[str] = None
    description: str
    requirements: str
    posted_by: str  # User ID
    posted_by_name: str
    logo: str = "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg?auto=compress&cs=tinysrgb&w=400"
    posted_date: datetime
    deadline: Optional[datetime] = None
    is_active: bool = True
    applicants: List[str] = []
    views: int = 0
    
    class Config:
        populate_by_name = True

class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    type: str
    salary: Optional[str]
    description: str
    requirements: str
    posted_by_name: str
    logo: str
    posted_date: str 
    deadline: Optional[datetime]
    is_active: bool
    applicants_count: int
    views: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "title": "Software Development Intern",
                "company": "Google",
                "location": "Bangalore, Karnataka",
                "type": "Internship",
                "salary": "₹50,000 - ₹80,000/month",
                "description": "Join our team to work on cutting-edge technology.",
                "requirements": "Strong coding skills in Java/Python",
                "posted_by_name": "Amit Kumar",
                "logo": "https://example.com/logo.jpg",
                "posted_date": "2 days ago",
                "deadline": "2025-12-31T23:59:59",
                "is_active": True,
                "applicants_count": 45,
                "views": 234
            }
        }

class PostCreate(BaseModel):
    content: str
    image: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Just got selected for Google Summer of Code 2024!",
                "image": "https://images.pexels.com/photos/1181675/pexels-photo-1181675.jpeg"
            }
        }

class PostUpdate(BaseModel):
    content: Optional[str] = None
    image: Optional[str] = None

class CommentCreate(BaseModel):
    content: str

class Comment(BaseModel):
    author_id: str
    author_name: str
    author_picture: str
    content: str
    created_at: datetime

class PostInDB(BaseModel):
    id: str = Field(alias="_id")
    author_id: str
    author_name: str
    author_registration_number: str
    author_department: str
    author_profile_picture: str
    content: str
    image: Optional[str] = None
    likes: List[str] = []  # List of user IDs
    comments: List[dict] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

class AuthorInfo(BaseModel):
    name: str
    registration_number: str
    department: str
    profile_picture: str

class PostResponse(BaseModel):
    id: str
    author: AuthorInfo
    content: str
    image: Optional[str]
    likes: int
    comments: int
    timestamp: str  # Human-readable format
    is_liked: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "author": {
                    "name": "Priya Patel",
                    "registration_number": "2020UEC5678",
                    "department": "Electronics & Communication",
                    "profile_picture": "https://example.com/pic.jpg"
                },
                "content": "Just got selected for Google Summer of Code 2024!",
                "image": "https://example.com/image.jpg",
                "likes": 234,
                "comments": 45,
                "timestamp": "3 hours ago",
                "is_liked": False
            }
        }

class CommentResponse(BaseModel):
    author_name: str
    author_picture: str
    content: str
    created_at: datetime