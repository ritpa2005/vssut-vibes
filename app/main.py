from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.cache import cache
from app.core.config import settings
from app.core.limiter import limiter, rate_limit_exceeded_handler
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.db.database import connect_to_mongo, close_mongo_connection
from app.db.indexes import create_all_indexes
from app.routers import auth, users, jobs, posts, rooms

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="VSSUT Vibes API — connecting students and alumni of VSSUT Burla.",
)

app.state.limiter = limiter

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    await create_all_indexes()
    print(f"{settings.APP_NAME} v{settings.VERSION} started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "VSSUT Vibes API",
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "base_url": settings.BASE_URL,
    }

# Debug endpoint (Not for production)
@app.get("/cache/stats")
async def cache_stats():
    """Shows current cache contents. Remove before going live."""
    return cache.stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)