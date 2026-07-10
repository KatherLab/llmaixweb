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
import platform
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from ._version import get_git_commit, get_version
from .celery.celery_config import celery_app
from .core.dynamic_settings import get_settings
from .core.rate_limit import limiter
from .core.security import admin_has_global_project_access
from .db.session import init_db
from .middleware.error_handlers import register_exception_handlers
from .middleware.request_context import RequestContextMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .routers.v1.endpoints import (
    admin,
    admin_sso,
    audit,
    auth,
    projects,
    sso,
    users,
)
from .utils.logging_config import setup_logging
from .websocket_manager import manager

# Use dynamic settings (includes database overrides from admin UI)
settings = get_settings()

logger = logging.getLogger(__name__)


def _resolve_project_owner(data: dict) -> int | None:
    """Resolve the owner user id for a task-update payload's project.

    Returns the ``Project.owner_id`` for the payload's ``project_id``, or
    ``None`` if the payload has no project id, the project was deleted, or the
    DB is unavailable. ``None`` means the update is delivered to admins only
    (never to a non-owner), so a missing/unknown project never leaks an update
    to the wrong user. The query is a single point lookup by project id.
    """
    project_id = data.get("project_id")
    if project_id is None:
        return None
    try:
        from sqlalchemy import select

        from .db.session import SessionLocal
        from .models.project import Project

        db = SessionLocal()
        try:
            owner_id = db.execute(
                select(Project.owner_id).where(Project.id == project_id)
            ).scalar_one_or_none()
            return owner_id
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Could not resolve owner for project {project_id}: {e}")
        return None


def _resolve_celery_pool(pool: str) -> str:
    """Resolve a Celery worker pool name, handling the ``auto`` sentinel.

    ``auto`` → ``solo`` on macOS (native OCR libraries like Tesseract/Paddle
    are not thread/fork-safe and crash under prefork on Darwin), ``prefork``
    elsewhere. Explicit values (``solo``/``prefork``/``threads``/…) pass
    through unchanged.
    """
    pool = (pool or "").strip().lower()
    if pool == "auto":
        return "solo" if platform.system() == "Darwin" else "prefork"
    return pool or "threads"


def _spawn_celery_worker(
    queue: str, concurrency: int, pool: str | None = None, with_beat: bool = False
) -> mp.Process:
    """
    Start ONE Celery worker process listening on <queue>.

    ``pool`` overrides the pool type for this queue; when omitted it falls back
    to the ``CELERY_DEV_POOL`` env var (default ``threads``). The preprocess
    queue should pass ``settings.CELERY_PREPROCESS_POOL`` so the heavy OCR
    worker uses a native-library-safe pool (solo on macOS).

    ``with_beat`` embeds the beat scheduler (``-B``) in this worker so the
    periodic orphan/stuck-task sweeper actually runs. Enable it on exactly ONE
    worker (the single ``default`` worker) — the periodic schedule is
    registered via ``on_after_configure``/``add_periodic_task`` but nothing
    fires it without a beat process. Do not enable on more than one worker or
    the sweep would run in duplicate.
    """
    resolved_pool = _resolve_celery_pool(
        pool if pool is not None else os.getenv("CELERY_DEV_POOL", "threads")
    )
    argv = [
        "worker",
        "-Q",
        queue,
        "-c",
        str(concurrency),
        "--max-tasks-per-child",
        "5",
        "--pool",
        resolved_pool,
        "--loglevel",
        "info",
        "-n",
        f"{queue}@%(hostname)s",  # unique node‑name → no warnings
    ]
    if with_beat:
        # Embed beat + use an in-memory schedule so no celerybeat-schedule file
        # is written to the container filesystem.
        argv += ["-B", "-s", "/tmp/celerybeat-schedule"]

    assert celery_app is not None  # guarded by caller (INITIALIZE_CELERY block)
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
    from .utils.redis_broadcast import (
        SETTINGS_INVALIDATE_CHANNEL,
        TASK_UPDATE_CHANNEL,
    )

    try:
        from .utils.redis_broadcast import new_dedicated_redis_client

        redis_client = new_dedicated_redis_client()
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
        # Subscribe to task updates (for WebSocket fan-out) AND settings
        # invalidation. Without the latter, a settings change made on ANOTHER
        # web replica never reaches this process's @lru_cache'd settings, so it
        # would serve stale config until restart. (The saving replica reloads
        # its own cache directly; Celery workers get it via their own
        # subscriber — this closes the gap for multi-replica web deployments.)
        pubsub.subscribe(TASK_UPDATE_CHANNEL, SETTINGS_INVALIDATE_CHANNEL)
        logger.info(
            "Subscribed to Redis channels: %s, %s",
            TASK_UPDATE_CHANNEL,
            SETTINGS_INVALIDATE_CHANNEL,
        )

        # Yield control back to event loop so startup can complete
        await asyncio.sleep(0)

        # Use get_message with short timeout for responsive async loop.
        # redis-py's pubsub.get_message() is a BLOCKING call; running it
        # directly on the event loop stalls all async handlers (including
        # WebSocket broadcasts) for the full timeout window each iteration.
        # Offload it to a worker thread so the loop stays responsive.
        while True:
            try:
                # Short timeout (100ms) so we don't block shutdown
                message = await asyncio.to_thread(pubsub.get_message, timeout=0.1)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    if data.get("type") == "settings_invalidate":
                        # Reload this replica's cached settings. broadcast=False
                        # so we don't re-publish and loop.
                        from .core.dynamic_settings import reload_settings_cache

                        await asyncio.to_thread(
                            reload_settings_cache, broadcast=False
                        )
                        continue
                    # Filter server-side by project ownership: deliver only to
                    # the project owner + admins. Previously this was broadcast
                    # to every connected user and the frontend was trusted to
                    # filter — a client that didn't filter could observe other
                    # users' task progress/metadata.
                    owner_id = await asyncio.to_thread(_resolve_project_owner, data)
                    await manager.broadcast_to_project(owner_id, data)
            except Exception as e:
                logger.error(f"Redis message processing error: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("Redis subscriber task cancelled")
    finally:
        try:
            if pubsub is not None:
                pubsub.unsubscribe()
            redis_client.close()
        except Exception:
            pass


async def _log_public_url():
    """Surface the configured public origin so users know how to reach the app.

    uvicorn logs its bind address (e.g. http://0.0.0.0:8000), which is the
    internal container address — in the compose stack the app is reached via
    the frontend nginx proxy at APP_URL, not the backend's bind address.
    Scheduled after startup completes (uvicorn prints its "running on" line
    only after the lifespan yields) so this lands cleanly below it rather than
    being buried mid-startup.
    """
    # Let uvicorn's own startup-complete lines flush first.
    await asyncio.sleep(0.5)
    # Always state how the app is reached; if APP_URL is the default, that's
    # almost certainly wrong in a compose deployment — warn and tell the user
    # to set it, but still show the URL so they know what's currently in use.
    # APP_URL is the public frontend origin (the nginx proxy in compose), i.e.
    # how users reach the full app — not the backend's internal bind address.
    is_default = settings.APP_URL == "http://localhost:5173"
    logger.warning(
        "🌐 LLMAIx-v2 is reachable at: %s%s",
        settings.APP_URL,
        (
            " (APP_URL is not set — configure the public origin, used for SSO "
            "redirects, share links, etc.)"
            if is_default
            else ""
        ),
    )


@asynccontextmanager
async def lifespan(app):
    setup_logging(level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info(
        "Starting %s v%s (%s)",
        settings.PROJECT_NAME,
        get_version(),
        get_git_commit(),
    )
    init_db()

    # Re-load DB-backed admin overrides now that the DB exists. ``settings``
    # is lru-cached at import time (before init_db), so on a fresh startup the
    # app_settings table didn't exist yet and overrides were skipped. Reload so
    # admin-configured values (e.g. disabled OCR engines) apply immediately.
    try:
        from .core.dynamic_settings import reload_settings_cache

        reload_settings_cache(broadcast=False)
    except Exception as e:
        logger.warning("Failed to reload DB settings overrides on startup: %s", e)

    workers: list[mp.Process] = []
    if celery_app is not None and settings.INITIALIZE_CELERY:
        # 1) general‑purpose tasks. Embed beat here (single default worker) so
        # the periodic orphan/stuck-task sweeper runs.
        workers.append(_spawn_celery_worker("default", concurrency=4, with_beat=True))

        # 2) heavy OCR / preprocessing tasks — use the preprocess-specific pool
        # (CELERY_PREPROCESS_POOL, defaults to "auto" → solo on macOS for
        # native OCR library safety) rather than the generic CELERY_DEV_POOL.
        workers.append(
            _spawn_celery_worker(
                "preprocess", concurrency=1, pool=settings.CELERY_PREPROCESS_POOL
            )
        )

    # Start Redis subscriber in background (non-blocking, optional)
    redis_task = None
    if settings.CELERY_BROKER_URL.startswith("redis://"):
        try:
            # Create task but don't await it - runs in background
            redis_task = asyncio.create_task(_redis_subscriber_task())
            logger.info("🚀 Redis subscriber task started in background")
        except Exception as e:
            logger.debug(f"Redis subscriber not started: {e}")

    # Print the public app URL as the last startup line (after uvicorn's own
    # "running on" line, which is logged only once this lifespan yields).
    url_task = asyncio.create_task(_log_public_url())

    try:
        yield
    finally:
        if redis_task:
            redis_task.cancel()
            try:
                await redis_task
            except asyncio.CancelledError:
                pass
        url_task.cancel()
        try:
            await url_task
        except asyncio.CancelledError:
            pass

        for p in workers:
            if p.is_alive():
                p.terminate()
                p.join(5)


app = FastAPI(lifespan=lifespan, redirect_slashes=False)

# ── Rate limiting ──────────────────────────────────────────────
# Shared limiter instance (Redis-backed when the broker is Redis, so counters
# are shared across workers; memory-backed otherwise). See core/rate_limit.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(sso.router, prefix="/auth/sso", tags=["sso"])
api_router.include_router(users.router, prefix="/user", tags=["users"])
api_router.include_router(projects.router, prefix="/project", tags=["projects"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_sso.router, prefix="/admin/sso", tags=["admin-sso"])
api_router.include_router(audit.router, prefix="/admin", tags=["audit"])
app.include_router(api_router)

# Global exception handling: unhandled errors get a correlation id, a logged
# traceback, an error_logs row, and a safe {error_id, message} response.
register_exception_handlers(app)

logger.info("CORS origins: %s", settings.BACKEND_CORS_ORIGINS_LIST)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware added later wraps the ones added earlier, so these two end up
# OUTSIDE CORS: RequestContext (outermost) stamps the correlation id before any
# handler runs, and SecurityHeaders decorates every response. HSTS is emitted
# only over HTTPS (or X-Forwarded-Proto: https behind the reverse proxy).
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)


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

    Authentication: the JWT is passed via the ``Sec-WebSocket-Protocol`` header
    as ``access_token, <jwt>`` (kept out of the URL so it doesn't leak into
    proxy/access logs). The negotiated ``access_token`` subprotocol is echoed
    back on accept. The legacy ``?token=`` query-string form has been removed.
    """
    from sqlalchemy import select

    from .core.dynamic_settings import get_settings
    from .db.session import SessionLocal
    from .models.user import User

    settings = get_settings()

    # Token-in-subprotocol only: the client sends
    # Sec-WebSocket-Protocol: access_token, <jwt>
    token: str | None = None
    accepted_subprotocol: str | None = None
    protocols = [
        p.strip()
        for p in (websocket.headers.get("sec-websocket-protocol") or "").split(",")
        if p.strip()
    ]
    if len(protocols) >= 2 and protocols[0] == "access_token":
        token = protocols[1]
        accepted_subprotocol = "access_token"

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
        user_id: str | None = payload.get("sub")
        if user_id is None:
            await websocket.close(code=4401, reason="Invalid token")
            return
        # Malformed "sub" (non-int) → treat as invalid token rather than a 500.
        user_id_int = int(user_id)

        # Get user from database
        db = SessionLocal()
        try:
            user = (
                db.execute(select(User).where(User.id == user_id_int))
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

    # Connect the WebSocket. connect() returns False if the per-user
    # connection cap was hit (it already closed the socket with 1013), in
    # which case there's nothing to loop on.
    connected = await manager.connect(
        websocket,
        user_id=user.id,
        # Only admins with cross-user project access join the admin broadcast
        # bucket, which receives every project's task updates. Without global
        # access (the default) an admin is scoped to their own projects, so
        # they must not observe other users' task progress.
        is_admin=admin_has_global_project_access(user),
        subprotocol=accepted_subprotocol,
    )
    if not connected:
        return

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
