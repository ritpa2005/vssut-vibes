from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.utils.security import decode_token
from app.database import get_users_collection
from bson import ObjectId

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login/json")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    try:
        user_obj_id = ObjectId(user_id)
    except:
        raise credentials_exception
    
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"_id": ObjectId(user_obj_id)})
    
    if user is None:
        raise credentials_exception
    
    user["_id"] = str(user["_id"])
    user["connections"] = [str(conn) for conn in user.get("connections", [])]
    
    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user