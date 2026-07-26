import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

FOLDER_PROFILES = "vssut-vibes/profiles"
FOLDER_POSTS    = "vssut-vibes/posts"
FOLDER_JOBS     = "vssut-vibes/jobs"

DEFAULT_PROFILE = "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&w=400"
DEFAULT_JOB     = "https://images.pexels.com/photos/270637/pexels-photo-270637.jpeg?auto=compress&cs=tinysrgb&w=400"

async def upload_image(
    file:           UploadFile,
    folder:         str,
    transformation: list = None
) -> str:
    """
    Upload a file to Cloudinary and return its secure URL.
    transformation — optional list of Cloudinary transformation dicts.
    Raises ValueError if the file is not a valid image type.
    """
    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed:
        raise ValueError(f"Unsupported file type: {file.content_type}. Allowed: jpeg, png, gif, webp")

    contents = await file.read()

    upload_options = {
        "folder":          folder,
        "resource_type":   "image",
        "transformation":  transformation or [],
    }

    result = cloudinary.uploader.upload(contents, **upload_options)
    return result["secure_url"]


async def delete_image(public_id: str) -> None:
    """
    Delete an image from Cloudinary by its public_id.
    Use when replacing a profile picture or deleting a post with an image.
    public_id is the path without extension, e.g. 'vssut-vibes/profiles/abc123'
    """
    cloudinary.uploader.destroy(public_id)


# ── Domain-specific upload functions ─────────────────────────────────────────

async def upload_profile_picture(file: UploadFile | None) -> str:
    """
    Upload a profile picture.
    Auto-crops to a 400x400 face-focused square.
    Returns default avatar URL if no file provided.
    """
    if not file:
        return DEFAULT_PROFILE

    return await upload_image(
        file=file,
        folder=FOLDER_PROFILES,
        transformation=[
            {
                "width":   400,
                "height":  400,
                "crop":    "fill",
                "gravity": "face"   # centres the crop on the face
            }
        ]
    )


async def upload_post_image(file: UploadFile | None) -> str | None:
    """
    Upload a post image.
    Resizes to max 1200px wide while preserving aspect ratio.
    Returns None if no file provided.
    """
    if not file:
        return None

    return await upload_image(
        file=file,
        folder=FOLDER_POSTS,
        transformation=[
            {
                "width":   1200,
                "crop":    "limit",   # only shrinks, never upscales
                "quality": "auto",    # Cloudinary picks the best quality/size trade-off
                "fetch_format": "auto"  # serves WebP to browsers that support it
            }
        ]
    )


async def upload_job_logo(file: UploadFile | None) -> str:
    """
    Upload a company logo.
    Pads to a 200x200 square with white background (logos aren't always square).
    Returns default job image if no file provided.
    """
    if not file:
        return DEFAULT_JOB

    return await upload_image(
        file=file,
        folder=FOLDER_JOBS,
        transformation=[
            {
                "width":      200,
                "height":     200,
                "crop":       "pad",
                "background": "white"
            }
        ]
    )