from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import auth, users, jobs, posts

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="VSSUT Vibes API for connecting students and alumni.",
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print(f"{settings.APP_NAME} v{settings.VERSION} started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(posts.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "VSSUT Vibes API",
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)