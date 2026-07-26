from app.repositories.room_repo import create_indexes as create_room_indexes
 
 
async def create_all_indexes() -> None:
    await create_room_indexes()