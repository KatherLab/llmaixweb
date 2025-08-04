from __future__ import annotations

import multiprocessing as mp
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from llmaix.__version__ import __version__

from .celery.celery_config import celery_app
from .core.config import settings
from .db.session import init_db
from .routers.v1.endpoints import admin, auth, projects, users


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
        "--loglevel",
        "info",
        "-n",
        f"{queue}@%(hostname)s",  # unique node‑name → no warnings
    ]

    proc = mp.Process(
        target=celery_app.worker_main,
        args=(argv,),
        daemon=True,  # dies with parent
        name=f"celery-{queue}-worker",
    )
    proc.start()
    return proc


# ───────────────────────── FastAPI lifespan ──────────────────────
@asynccontextmanager
async def lifespan(app):
    init_db()

    workers: list[mp.Process] = []
    if celery_app is not None and settings.INITIALIZE_CELERY:
        # 1) general‑purpose tasks
        workers.append(_spawn_celery_worker("default", concurrency=4))

        # 2) heavy OCR / preprocessing tasks
        workers.append(_spawn_celery_worker("preprocess", concurrency=1))

    try:
        yield
    finally:
        for p in workers:
            if p.is_alive():
                p.terminate()
                p.join(5)


app = FastAPI(lifespan=lifespan)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/user", tags=["users"])
api_router.include_router(projects.router, prefix="/project", tags=["projects"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(api_router)

print("Using custom CORS origins from settings:", settings.BACKEND_CORS_ORIGINS_LIST)
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
    return {"version": __version__, "description": "LLMAIx (v2) backend API"}
