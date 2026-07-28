from app.db.database import (
    get_users_collection,
    get_posts_collection,
    get_jobs_collection,
    get_rooms_collection,
)


async def create_user_indexes() -> None:
    col = await get_users_collection()

    await col.create_index("email", unique=True)
    await col.create_index("registration_number", unique=True)
    await col.create_index("department")
    await col.create_index("skills")
    await col.create_index("connections")
    await col.create_index([("name", "text")])

    print("User indexes created.")


async def create_post_indexes() -> None:
    col = await get_posts_collection()

    await col.create_index([("created_at", -1)])
    await col.create_index("author_id")
    await col.create_index([("author_id", 1), ("created_at", -1)])

    print("Post indexes created.")


async def create_job_indexes() -> None:
    col = await get_jobs_collection()

    await col.create_index([("posted_date", -1)])
    await col.create_index("type")
    await col.create_index("is_active")
    await col.create_index([("is_active", 1), ("posted_date", -1)])
    await col.create_index("posted_by")

    print("Job indexes created.")


async def create_room_indexes() -> None:
    col = await get_rooms_collection()

    await col.create_index("invite_code", unique=True)
    await col.create_index("mentor_id")
    await col.create_index("members")
    await col.create_index([("updated_at", -1)])

    print("Room indexes created.")


async def create_all_indexes() -> None:
    print("Creating indexes...")
    await create_user_indexes()
    await create_post_indexes()
    await create_job_indexes()
    await create_room_indexes()
    print("All indexes ready.")