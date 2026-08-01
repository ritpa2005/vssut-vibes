from app.db.database import get_users_collection


async def find_by_email(email: str) -> dict | None:
    col = await get_users_collection()
    return await col.find_one({"email": email})

async def find_by_email_or_registration(email: str, registration_number: str) -> dict | None:
    col = await get_users_collection()
    return await col.find_one({
        "$or": [
            {"email": email},
            {"registration_number": registration_number}
        ]
    })

async def create_user(user_dict: dict) -> str:
    """Insert a new user document and return the inserted ID as string."""
    col = await get_users_collection()
    result = await col.insert_one(user_dict)
    return str(result.inserted_id)