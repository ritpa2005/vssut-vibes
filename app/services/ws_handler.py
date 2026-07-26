from bson import ObjectId
from app.core.security import decode_token
from app.db.database import get_users_collection


async def get_ws_user(token: str) -> dict | None:
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    users_col = await get_users_collection()
    user      = await users_col.find_one({"_id": ObjectId(user_id)})

    if user:
        user["_id"] = str(user["_id"])
    return user