from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from app.models import PostCreate, PostUpdate, CommentCreate, PostResponse, CommentResponse, AuthorInfo
from app.utils.dependencies import get_current_active_user
from app.database import get_posts_collection
from typing import List
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/posts", tags=["Posts"])

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

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str = Form(...),
    image: UploadFile = File(None),
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    image_url = None
    if image:
        file_bytes = await image.read()
        file_name = f"post_{datetime.utcnow().timestamp()}.jpg"
        with open(f"media/posts/{file_name}", "wb") as f:
            f.write(file_bytes)
        image_url = f"/media/posts/{file_name}"

    
    post_dict = {
        "author_id": current_user["_id"],
        "author_name": current_user["name"],
        "author_registration_number": current_user["registration_number"],
        "author_department": current_user["department"],
        "author_profile_picture": current_user.get("profile_picture", ""),
        "content": content,
        "image": image_url,
        "likes": [],
        "comments": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await posts.insert_one(post_dict)
    
    return PostResponse(
        id=str(result.inserted_id),
        author=AuthorInfo(
            name=post_dict["author_name"],
            registration_number=post_dict["author_registration_number"],
            department=post_dict["author_department"],
            profile_picture=post_dict["author_profile_picture"]
        ),
        content=post_dict["content"],
        image=post_dict["image"],
        likes=0,
        comments=0,
        timestamp=format_time_ago(post_dict["created_at"]),
        is_liked=False
    )

@router.get("/", response_model=List[PostResponse])
async def get_posts(
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    cursor = posts.find().sort("created_at", -1).skip(skip).limit(limit)
    posts = await cursor.to_list(length=limit)
    
    return [
        PostResponse(
            id=str(post["_id"]),
            author=AuthorInfo(
                name=post["author_name"],
                registration_number=post["author_registration_number"],
                department=post["author_department"],
                profile_picture=post["author_profile_picture"]
            ),
            content=post["content"],
            image=post.get("image"),
            likes=len(post.get("likes", [])),
            comments=len(post.get("comments", [])),
            timestamp=format_time_ago(post["created_at"]),
            is_liked=current_user["_id"] in post.get("likes", [])
        )
        for post in posts
    ]

@router.get("/{post_id}", response_model=PostResponse)
async def get_post_by_id(
    post_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    try:
        post = await posts.find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return PostResponse(
        id=str(post["_id"]),
        author=AuthorInfo(
            name=post["author_name"],
            registration_number=post["author_registration_number"],
            department=post["author_department"],
            profile_picture=post["author_profile_picture"]
        ),
        content=post["content"],
        image=post.get("image"),
        likes=len(post.get("likes", [])),
        comments=len(post.get("comments", [])),
        timestamp=format_time_ago(post["created_at"]),
        is_liked=current_user["_id"] in post.get("likes", [])
    )

@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    try:
        post = await posts.find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    likes = post.get("likes", [])
    
    if current_user["_id"] in likes:
        await posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$pull": {"likes": current_user["_id"]}}
        )
        message = "Post unliked"
        likes_count = len(likes) - 1
    else:
        await posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$push": {"likes": current_user["_id"]}}
        )
        message = "Post liked"
        likes_count = len(likes) + 1
    
    return {
        "message": message,
        "likes_count": likes_count
    }


@router.post("/{post_id}/comment", response_model=CommentResponse)
async def add_comment(
    post_id: str,
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    try:
        post = await posts.find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    comment = {
        "author_id": current_user["_id"],
        "author_name": current_user["name"],
        "author_picture": current_user.get("profile_picture", ""),
        "content": comment_data.content,
        "created_at": datetime.utcnow()
    }
    
    await posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$push": {"comments": comment}}
    )
    
    return CommentResponse(
        author_name=comment["author_name"],
        author_picture=comment["author_picture"],
        content=comment["content"],
        created_at=comment["created_at"]
    )


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def get_comments(post_id: str):
    posts = await get_posts_collection()
    
    try:
        post = await posts.find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    comments = post.get("comments", [])
    
    return [
        CommentResponse(
            author_name=comment["author_name"],
            author_picture=comment["author_picture"],
            content=comment["content"],
            created_at=comment["created_at"]
        )
        for comment in comments
    ]


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post_update: PostUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    try:
        post = await posts.find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if post["author_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this post"
        )
    
    update_data = post_update.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": update_data}
        )
        post = await posts.find_one({"_id": ObjectId(post_id)})
    
    return PostResponse(
        id=str(post["_id"]),
        author=AuthorInfo(
            name=post["author_name"],
            registration_number=post["author_registration_number"],
            department=post["author_department"],
            profile_picture=post["author_profile_picture"]
        ),
        content=post["content"],
        image=post.get("image"),
        likes=len(post.get("likes", [])),
        comments=len(post.get("comments", [])),
        timestamp=format_time_ago(post["created_at"]),
        is_liked=current_user["_id"] in post.get("likes", [])
    )

@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    try:
        post = await posts.find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if post["author_id"] != current_user["_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this post"
        )
    
    await posts.delete_one({"_id": ObjectId(post_id)})
    
    return {"message": "Post deleted successfully"}

@router.get("/user/{user_id}", response_model=List[PostResponse])
async def get_user_posts(
    user_id: str,
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    posts = await get_posts_collection()
    
    cursor = posts.find(
        {"author_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    posts = await cursor.to_list(length=limit)
    
    return [
        PostResponse(
            id=str(post["_id"]),
            author=AuthorInfo(
                name=post["author_name"],
                registration_number=post["author_registration_number"],
                department=post["author_department"],
                profile_picture=post["author_profile_picture"]
            ),
            content=post["content"],
            image=post.get("image"),
            likes=len(post.get("likes", [])),
            comments=len(post.get("comments", [])),
            timestamp=format_time_ago(post["created_at"]),
            is_liked=current_user["_id"] in post.get("likes", [])
        )
        for post in posts
    ]