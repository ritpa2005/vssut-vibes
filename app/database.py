from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None
    
db = Database()

async def get_database():
    return db.client[settings.DATABASE_NAME]

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)
    print("Connected to MongoDB Atlas!")

async def close_mongo_connection():
    db.client.close()
    print("Closed MongoDB connection!")

async def get_users_collection():
    database = await get_database()
    return database["users"]

async def get_jobs_collection():
    database = await get_database()
    return database["jobs"]

async def get_posts_collection():
    database = await get_database()
    return database["posts"]