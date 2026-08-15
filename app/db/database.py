from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    
db = Database()

async def get_database():
    return db.client[settings.DATABASE_NAME]

async def connect_to_mongo():
    db.client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        maxPoolSize=50,        # max connections per Motor client instance
        minPoolSize=10,        # keep 10 warm — avoids cold-start latency on burst
        maxIdleTimeMS=45000,            # close idle connections after 45s
        serverSelectionTimeoutMS=5000,  # fail fast if Atlas is unreachable
        connectTimeoutMS=10000,         # max time to establish a new connection
        socketTimeoutMS=30000,          # max time waiting for a response on a socket
    )
    print("Connected to MongoDB Atlas!")

async def close_mongo_connection():
    if db.client:
        db.client.close()
        print("Closed MongoDB connection.")

async def get_users_collection():
    database = await get_database()
    return database["users"]

async def get_jobs_collection():
    database = await get_database()
    return database["jobs"]

async def get_posts_collection():
    database = await get_database()
    return database["posts"]

async def get_rooms_collection():
    database = await get_database()
    return database["rooms"]