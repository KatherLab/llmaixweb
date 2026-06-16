# backend/src/main.py
from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing as mp

try:
    mp.set_start_method("spawn")
except RuntimeError:
    pass

import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ._version import get_git_commit, get_version
from .celery.celery_config import celery_app
from .core.dynamic_settings import get_settings
from .db.session import init_db
from .routers.v1.endpoints import admin, auth, projects, users
from .utils.logging_config import setup_logging
from .websocket_manager import manager

# Use dynamic settings (includes database overrides from admin UI)
settings = get_settings()

logger = logging.getLogger(__name__)


def _spawn_celery_worker(queue: str, concurrency: int) -> mp.Process:
    """
    Start ONE Celery worker process listening on <queue> using Celery’s
    default prefork pool (so logs go straight to your terminal).
    """
    argv = [
        "worker",
        "-Q",
        queue,
        "-c",
        str(concurrency),
        "--max-tasks-per-child",
        "5",
        "--pool",
        os.getenv("CELERY_DEV_POOL", "threads"),
        "--loglevel",
        "info",
        "-n",
        f"{queue}@%(hostname)s",  # unique node‑name → no warnings
    ]

    proc = mp.Process(
        target=celery_app.worker_main,
        args=(argv,),
        daemon=False,  # dies with parent
        name=f"celery-{queue}-worker",
    )
    proc.start()
    return proc


# ───────────────────────── FastAPI lifespan ──────────────────────
async def _redis_subscriber_task():
    """Background task that subscribes to Redis task updates and broadcasts via WebSocket.

    Runs in the background without blocking startup. If Redis is unavailable,
    the task simply doesn't run - Celery workers will still work, just without
    real-time progress updates.
    """
    from .utils.redis_broadcast import TASK_UPDATE_CHANNEL

    try:
        from .utils.redis_broadcast import get_redis_client

        redis_client = get_redis_client()
        if not redis_client:
            logger.warning(
                "Redis not available - real-time Celery task updates disabled"
            )
            return
        logger.info("Connected to Redis for task updates")
    except Exception as e:
        logger.warning(
            f"Redis connection failed: {e} - real-time Celery task updates disabled"
        )
        return

    try:
        pubsub = redis_client.pubsub()
        pubsub.subscribe(TASK_UPDATE_CHANNEL)
        logger.info("Subscribed to Redis channel: %s", TASK_UPDATE_CHANNEL)

        # Yield control back to event loop so startup can complete
        await asyncio.sleep(0)

        # Use get_message with short timeout for responsive async loop
        while True:
            try:
                # Short timeout (100ms) so we don't block shutdown
                message = pubsub.get_message(timeout=0.1)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    # Broadcast to all connected clients (admin + all users)
                    # The frontend filters by project_id on its end
                    await manager.broadcast_to_all(data)
                # Small sleep to prevent tight loop when no messages
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Redis message processing error: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("Redis subscriber task cancelled")
    finally:
        try:
            pubsub.unsubscribe()
            redis_client.close()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app):
    setup_logging(level=settings.LOG_LEVEL)
    logger.info(
        "Starting %s v%s (%s)",
        settings.PROJECT_NAME,
        get_version(),
        get_git_commit(),
    )
    init_db()

    workers: list[mp.Process] = []
    if celery_app is not None and settings.INITIALIZE_CELERY:
        # 1) general‑purpose tasks
        workers.append(_spawn_celery_worker("default", concurrency=4))

        # 2) heavy OCR / preprocessing tasks
        workers.append(_spawn_celery_worker("preprocess", concurrency=1))

    # Start Redis subscriber in background (non-blocking, optional)
    redis_task = None
    if settings.CELERY_BROKER_URL.startswith("redis://"):
        try:
            # Create task but don't await it - runs in background
            redis_task = asyncio.create_task(_redis_subscriber_task())
            logger.info("🚀 Redis subscriber task started in background")
        except Exception as e:
            logger.debug(f"Redis subscriber not started: {e}")

    try:
        yield
    finally:
        if redis_task:
            redis_task.cancel()
            try:
                await redis_task
            except asyncio.CancelledError:
                pass

        for p in workers:
            if p.is_alive():
                p.terminate()
                p.join(5)


app = FastAPI(lifespan=lifespan, redirect_slashes=False)

# ── Rate limiting ──────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/user", tags=["users"])
api_router.include_router(projects.router, prefix="/project", tags=["projects"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(api_router)

logger.info("CORS origins: %s", settings.BACKEND_CORS_ORIGINS_LIST)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello, hello!"}


@app.get("/api/v1/version")
@app.get("/version")
async def version_api():
    """
    Returns backend version information.

    Backend version is read from pyproject.toml.
    Git commit hash is set at build time via GIT_COMMIT_HASH env var (GitHub Actions).
    For local builds, git commit shows "unknown" (may have uncommitted changes).

    Note for developers: When releasing, update both:
    - backend: version in pyproject.toml
    - frontend: version in frontend/version.js
    """
    return {
        "backend_version": get_version(),
        "backend_git_commit": get_git_commit(),
        "backend_description": "LLMAIx (v2) backend API",
    }


# ───────────────────────── WebSocket Endpoint ──────────────────────────
@app.websocket("/ws/activity")
async def activity_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time activity updates.
    Clients connect to receive live updates on preprocessing tasks and trials.

    Authentication: Token passed as query param ?token=<jwt_token>
    """
    from sqlalchemy import select

    from .core.dynamic_settings import get_settings
    from .db.session import SessionLocal
    from .models.user import User

    settings = get_settings()

    # Get token from query params
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=4401, reason="Missing authentication token")
        return

    # Validate token manually (without Depends which doesn't work in WebSocket)
    try:
        import jwt as pyjwt
        from jwt.exceptions import PyJWTError

        payload = pyjwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},  # Require expiration and subject
        )
        user_id: str = payload.get("sub")

        # Get user from database
        db = SessionLocal()
        try:
            user = (
                db.execute(select(User).where(User.id == int(user_id)))
                .scalars()
                .one_or_none()
            )
            if user is None:
                await websocket.close(code=4401, reason="User not found")
                return
            if not user.is_active:
                await websocket.close(code=4401, reason="User inactive")
                return

            # Validate token version
            token_version = payload.get("tkn_v", 0)
            if token_version < user.token_version:
                await websocket.close(code=4401, reason="Token revoked")
                return
        finally:
            db.close()
    except PyJWTError as e:
        logger.warning(f"WebSocket JWT error: {e}")
        await websocket.close(code=4401, reason="Invalid token")
        return
    except Exception as e:
        logger.warning(f"WebSocket auth error: {e}")
        await websocket.close(code=4401, reason="Authentication failed")
        return

    # Connect the WebSocket
    await manager.connect(websocket, user_id=user.id, is_admin=(user.role == "admin"))

    try:
        # Keep connection alive and handle ping/pong
        while True:
            try:
                # Wait for messages (mostly for keepalive)
                data = await websocket.receive_text()
                # Optionally handle client messages
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
    finally:
        manager.disconnect(websocket, user_id=user.id)
