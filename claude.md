# VSSUT Vibes — Backend Development Log

## Project Overview

**VSSUT Vibes** is a social networking platform for students and alumni of Veer Surendra Sai University of Technology (VSSUT), Burla, Odisha. The backend is a FastAPI application connected to MongoDB Atlas, with a separately built frontend.

**Core purpose:** Professional networking, real-time communication, job listings, and collaboration rooms for the VSSUT community.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Framework | FastAPI |
| Database | MongoDB via Motor (async driver) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Real-time | WebSockets (FastAPI native) |
| AI Moderation | Claude API (claude-sonnet-4-6) |
| Media Storage | Cloudinary |
| Rate Limiting | slowapi |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| HTTP Client | httpx (for Claude API calls) |

---

## Final Project Structure

```
vssut-vibes/
├── app/
│   ├── core/
│   │   ├── config.py          # Settings, env vars, BASE_URL, Cloudinary config
│   │   ├── security.py        # JWT creation/decode, bcrypt hash/verify
│   │   ├── dependencies.py    # FastAPI Depends() — get_current_user, get_current_active_user
│   │   ├── exceptions.py      # Typed HTTPException subclasses + global handlers + success()
│   │   ├── ws_manager.py      # WebSocket ConnectionManager with heartbeat timeout
│   │   ├── limiter.py         # slowapi Limiter instance + rate_limit_exceeded_handler
│   │   └── cache.py           # In-memory TTL cache, CacheTTL constants, CacheKey builders
│   │
│   ├── db/
│   │   ├── database.py        # Motor client, collection getters
│   │   └── indexes.py         # create_all_indexes() — all 4 collections
│   │
│   ├── models/                # (monolithic models.py kept, not split)
│   │   └── models.py          # All InDB entity shapes (UserInDB, PostInDB, JobInDB, RoomInDB etc.)
│   │
│   ├── schemas/               # Pydantic DTOs — request/response shapes
│   │   ├── auth.py            # LoginRequest, Token, AuthUserResponse
│   │   ├── user.py            # UserCreate, UserUpdate, UserResponse, user_to_response()
│   │   ├── post.py            # PostCreate, PostUpdate, CommentCreate, PostResponse,
│   │   │                      # CommentResponse, AuthorInfo, post_to_response(), comment_to_response()
│   │   ├── job.py             # JobCreate, JobUpdate, JobResponse, job_to_response()
│   │   ├── room.py            # RoomCreate, RoomUpdate, RoomResponse, RoomPreviewResponse,
│   │   │                      # MessageResponse, room_to_response(), message_to_response()
│   │   └── suggestion.py      # SuggestedUser, SuggestionsResponse
│   │
│   ├── repositories/          # Raw MongoDB queries only — no business logic
│   │   ├── auth_repo.py       # find_by_email, find_by_email_or_registration, create_user
│   │   ├── user_repo.py       # find_by_id, find_many, update_by_id, push/pull_connection
│   │   ├── post_repo.py       # insert, find_by_id, find_feed, find_by_author,
│   │   │                      # update_by_id, delete_by_id, push/pull_like, push_comment
│   │   ├── job_repo.py        # insert, find_by_id, find_many, increment_views,
│   │   │                      # update_by_id, set_inactive, push_applicant
│   │   ├── room_repo.py       # insert_room, find_by_id, find_by_invite_code,
│   │   │                      # find_by_member, update_by_id, set_inactive,
│   │   │                      # push/pull_member, insert_message, fetch_messages,
│   │   │                      # add_read_by, create_indexes, generate_invite_code
│   │   └── suggestion_repo.py # fetch_user_rooms, fetch_candidates,
│   │                          # fetch_by_department, fetch_by_skills
│   │
│   ├── services/              # Business logic only — no HTTP, no raw DB
│   │   ├── auth_service.py    # register_user, login_user
│   │   ├── user_service.py    # get_me, update_me, update_profile_picture, get_by_id,
│   │   │                      # search, connect, disconnect, get_suggestions*,
│   │   │                      # _invalidate_suggestions()
│   │   ├── post_service.py    # create, get_feed, get_by_id, get_by_author,
│   │   │                      # update, delete, toggle_like, add_comment,
│   │   │                      # get_comments, _invalidate_feed()
│   │   ├── job_service.py     # create, get_all, get_by_id, update, delete, apply,
│   │   │                      # _invalidate_job_list()
│   │   ├── room_service.py    # create, get_by_id, get_by_invite_code, get_user_rooms,
│   │   │                      # update, close, join, kick, leave,
│   │   │                      # save_message, get_messages, mark_read
│   │   ├── suggestion_service.py   # get_suggestions, get_suggestions_by_department,
│   │   │                           # get_suggestions_by_skills — all cached
│   │   ├── suggestion_scorer.py    # Pure scoring functions — no DB, no HTTP
│   │   │                           # score_candidate, rank_candidates,
│   │   │                           # rank_by_department, rank_by_skills,
│   │   │                           # build_shared_rooms_map
│   │   ├── moderation_service.py   # moderate_content() — calls Claude API
│   │   ├── cloudinary_service.py   # upload_profile_picture, upload_post_image,
│   │   │                           # upload_job_logo, upload_image, delete_image
│   │   └── ws_handler.py      # get_ws_user() — JWT decode for WebSocket auth
│   │
│   ├── routers/               # HTTP + WebSocket — thin handlers only
│   │   ├── auth.py            # POST /register (JSON), POST /login/json
│   │   ├── users.py           # GET+PUT /me, PATCH /me/picture,
│   │   │                      # GET /suggestions (3 routes),
│   │   │                      # GET /, POST+DELETE /connect/{id}, GET /{id}
│   │   ├── posts.py           # GET+POST /, GET /user/{id},
│   │   │                      # GET+PUT+DELETE /{id},
│   │   │                      # POST /{id}/like, POST+GET /{id}/comment(s)
│   │   ├── jobs.py            # GET+POST /, GET+PUT+DELETE /{id}, POST /{id}/apply
│   │   └── rooms.py           # GET+POST /, GET /join/{code}, POST /join/{code},
│   │                          # GET+PUT+DELETE /{id}, DELETE /{id}/members/{uid},
│   │                          # DELETE /{id}/leave, GET /{id}/messages,
│   │                          # WS /{id}/ws
│   │
│   ├── utils/
│   │   └── formatters.py      # format_time_ago() — shared by posts and jobs
│   │
│   └── main.py                # App factory, middleware, exception handlers,
│                              # startup (DB connect + indexes + cache cleanup),
│                              # router registration
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_posts.py
│   ├── test_jobs.py
│   └── test_rooms.py
│
├── datasets/                  # Seed data (not part of app package)
├── .env                       # Never committed
├── .gitignore
├── pytest.ini
└── requirements.txt
```

---

## Architecture Pattern

```
Router (HTTP) → Schema (DTO) → Service (logic) → Repository (DB) → MongoDB
```

### Layer responsibilities

| Layer | What it does | What it must NOT do |
| --- | --- | --- |
| `routers/` | Parse HTTP request, call service, return response | DB calls, business logic, ObjectId |
| `schemas/` | Define API shapes, validate in/out, mapping helpers | DB logic, business rules |
| `services/` | Business rules, orchestration, cache, call repos | Raw MongoDB queries, HTTP concerns |
| `repositories/` | Raw MongoDB queries, return plain dicts | Business logic, schema knowledge |
| `models/` | Document shapes as stored in MongoDB | API concerns |

---

## Key Features

### Authentication

- Form-free JSON registration (`POST /auth/register`) using `UserCreate` schema
- JWT tokens via python-jose, bcrypt password hashing via passlib
- `OAuth2PasswordBearer` for protected routes
- WebSocket auth via `?token=<jwt>` query param (HTTP headers not available on WS)

### Posts

- Feed with 1-minute cache — `is_liked` recalculated per-user on cache hit
- Image upload via Cloudinary (max 1200px, auto quality/format)
- **AI content moderation** on every create — text + image sent to Claude API
  - Flags: hate_speech, sexual, violence, harassment, spam, misinformation, nudity
  - Fail-open on API errors (post allowed through if moderation API is down)
- `toggle_like` uses read-then-write (two DB calls) — intentional, not optimized

### Jobs

- Job list cached 1 hour, job detail cached 5 minutes
- Logo upload via Cloudinary (200×200 padded square, white bg)
- Soft delete — `is_active: False` instead of actual deletion
- View count incremented on `GET /{job_id}`

### Connection Suggestions

- Cached 24 hours per user — invalidated immediately on connect/disconnect/skill update
- Scoring weights: department (+30), skills (+10 each, cap +50), shared rooms (+25 each, cap +75), alumni↔student (+10)
- `suggestion_scorer.py` contains pure scoring functions — no DB, unit testable without mocks
- Three endpoints: combined (`/suggestions`), department-only, skills-only

### Collaboration Rooms

- Unique invite codes via `secrets.token_urlsafe(12)` — 2^96 possible values
- MongoDB unique index on `invite_code` as DB-level safety net
- Retry loop (max 5) handles collision
- Messages stored embedded in room document (known scale limitation)
- **WebSocket real-time messaging** — one persistent connection per user per room
- **Heartbeat timeout** — connection closed after 5 minutes of silence (code 4008)
  - Watchdog task per connection checks every 60 seconds
  - Client must send `{ "type": "ping" }` every 30 seconds
  - `manager.update_ping()` resets the timer on each ping
  - `disconnect()` cancels the watchdog task cleanly
- **Parallel broadcast** via `asyncio.gather()` — all room members receive simultaneously

### Media Storage

- All uploads go to Cloudinary — no local `media/` folder
- Profile pictures: 400×400 face-crop
- Post images: max 1200px wide, auto quality, auto format (WebP for supported browsers)
- Job logos: 200×200 padded square, white background

---

## Database Indexes

```python
# users
email               (unique)
registration_number (unique)
department
skills              # powers $in queries for suggestion engine
connections
name                (text index for search)

# posts
created_at          (descending) # feed sort
author_id
(author_id, created_at)          # compound: user profile posts sorted

# jobs
posted_date         (descending)
type
is_active
(is_active, posted_date)         # compound: most common query
posted_by

# rooms
invite_code         (unique)
mentor_id
members
updated_at          (descending)
```

---

## Caching Strategy

**Implementation:** In-memory TTL cache (`app/core/cache.py`) — no Redis needed for single-server deployment. Background cleanup task runs every 10 minutes to evict expired keys.

| Cache | TTL | Key pattern | Invalidated by |
| --- | --- | --- | --- |
| Suggestions (all) | 24h | `suggestions:all:{user_id}` | connect, disconnect, skill update |
| Suggestions (dept) | 24h | `suggestions:dept:{user_id}` | same |
| Suggestions (skills) | 24h | `suggestions:skills:{user_id}` | same |
| Post feed | 1 min | `feed:{skip}:{limit}` | create, update, delete post |
| Job list | 1h | `jobs:{type}:{loc}:{co}:{q}:{skip}:{limit}` | create, update, deactivate job |
| Job detail | 5 min | `job:{job_id}` | update, deactivate, apply |

**Feed caching note:** `is_liked` is user-specific but feed is cached globally. Raw likes stored under `_likes` in cache, recalculated per-user via `post_to_response()` on cache hit.

**Like/comment counts:** Allowed to be up to 1 minute stale — `toggle_like` and `add_comment` do NOT invalidate feed cache. Only create/update/delete do.

---

## Rate Limiting

**Library:** slowapi — per-IP limits via `X-Forwarded-For` header in production.

| Route | Limit | Reason |
| --- | --- | --- |
| `POST /auth/register` | 5/min | Stops bulk account creation |
| `POST /auth/login/json` | 10/min | Stops brute force |
| `POST /posts/` | 10/min | Each call hits Claude API — cost control |
| `POST /posts/{id}/like` | 30/min | Stops like bots |
| `POST /posts/{id}/comment` | 15/min | Stops comment spam |
| `POST /jobs/` | 5/min | Stops fake job listings |
| `POST /jobs/{id}/apply` | 10/min | Stops application spam |
| `POST /users/connect/{id}` | 20/min | Stops connection spam |
| `GET /users/suggestions*` | 10/min | Expensive DB query |
| `PATCH /users/me/picture` | 5/min | Stops Cloudinary abuse |

**Error response shape:**

```json
{
  "success": false,
  "status": 429,
  "error": "Rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60
}
```

---

## API Response Shape

Every response follows the same envelope:

```json
// Success
{ "success": true, "message": "Connected successfully" }
{ "success": true, "message": "Job created", "data": { ...job } }

// Error
{ "success": false, "status": 404, "error": "User not found" }
{ "success": false, "status": 403, "error": "You don't have permission" }

// Validation error
{ "success": false, "status": 422, "error": "Validation failed",
  "errors": [{ "field": "email", "message": "...", "type": "..." }] }

// Moderation error (extra fields)
{ "success": false, "status": 422, "error": "Your post was not published...",
  "reason": "Contains hate speech", "category": "hate_speech" }

// Rate limit
{ "success": false, "status": 429, "error": "Rate limit exceeded...", "retry_after": 60 }
```

---

## WebSocket Protocol

**Connect:** `ws://host/api/rooms/{room_id}/ws?token=<jwt>`

**Client → Server:**

```json
{ "type": "ping" }
{ "type": "message", "content": "Hello!", "attachment": null }
```

**Server → Client:**

```json
{ "type": "pong" }
{ "type": "message", ...MessageResponse }
{ "type": "join",     "user_id": "...", "user_name": "..." }
{ "type": "leave",    "user_id": "...", "user_name": "..." }
{ "type": "kick",     "user_id": "..." }
{ "type": "presence", "online_users": [...] }
{ "type": "room_closed" }
{ "type": "error",    "detail": "..." }
```

**Close codes:**

| Code | Reason |
| --- | --- |
| 4000 | Room is closed |
| 4001 | Unauthorized (bad token) |
| 4003 | Not a member of this room |
| 4004 | Room not found |
| 4008 | Heartbeat timeout (5 min silence) |

---

## Environment Variables (.env)

```env
APP_NAME=VSSUT Vibes API
VERSION=1.0.0
DEBUG=True
BASE_URL=http://127.0.0.1:8000

MONGODB_URI=mongodb+srv://...
DATABASE_NAME=vssut_vibes

SECRET_KEY=<32+ char random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

---

## Requirements

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
motor==3.3.2
pymongo==4.6.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.1
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0
httpx==0.27.0
cloudinary==1.36.0
slowapi==0.1.9
```

---

## Known Decisions & Trade-offs

| Decision | Reason |
| --- | --- |
| Models stay in monolithic `models.py` | Not split — developer preference |
| No `__init__.py` files | Developer preference |
| No `ml_model.py` | Was never used, removed |
| Repositories return plain dicts | Pydantic validation happens at response boundary — no runtime overhead from InDB models |
| `toggle_like` uses two DB calls | Intentional — read then write, not optimized with atomic update |
| Feed cache is global, `is_liked` recalculated | Avoids per-user cache explosion while keeping correct like state |
| In-memory cache, not Redis | Single server deployment — Redis unnecessary at this scale |
| Messages embedded in room document | Known 16MB limit risk — acceptable for current scale |
| Moderation fails open | Availability over strictness — post allowed if Claude API is down |
| OAuth2 form login removed | JSON login endpoint is cleaner, form endpoint was duplicate |
| `MessageCreate` schema exists but unused | Dead code in `models.py` — WS messages sent as raw JSON frames |

---

## Tests

```
tests/
├── conftest.py       # Fixtures, factories (student_doc, alumni_doc, job_doc, post_doc, room_doc)
├── test_auth.py      # Register, duplicate check, login, wrong password
├── test_users.py     # /me, update, search, get by ID, connect, disconnect, suggestions
├── test_posts.py     # Create, moderation pass/fail, like toggle, comment, 403, not found
├── test_jobs.py      # Create, list, filter, get, view increment, apply, 403
└── test_rooms.py     # Create, list, preview, join, full room, close, kick, leave, messages
```

**Run:**

```bash
pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

All tests mock at the collection layer and patch `get_current_active_user`. Moderation service is mocked in post tests to avoid Claude API calls.

---

## Seed Data

MongoDB seed script generates 100 realistic users:

- ~25% alumni, ~75% students
- All departments represented
- 2–7 random skills per user
- Valid `pravatar.cc` avatar URLs
- Random LinkedIn/GitHub URLs
- All passwords: `password123` (bcrypt hashed)
- Registration numbers: e.g. `2022UCS1234`

**Run in mongosh:**

```bash
mongosh "mongodb+srv://<uri>" seed_users.js
```
