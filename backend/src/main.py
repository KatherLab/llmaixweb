from __future__ import annotations

from contextlib import asynccontextmanager
import multiprocessing as mp

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from llmaix.__version__ import __version__

from .celery.celery_config import celery_app
from .core.config import settings
from .db.session import init_db
from .routers.v1.endpoints import auth, projects, users


def _spawn_celery_worker(queue: str, concurrency: int) -> mp.Process:
    """
    Start one Celery worker in a **separate OS process**.

    queue        – name of the queue to listen on
    concurrency  – number of child processes the worker should spawn
    """
    argv = [
        "worker",
        "-Q", queue,
        "-c", str(concurrency),
        "--max-tasks-per-child", "5",     # recycle workers to limit RAM growth
        "--loglevel", "info",
    ]
    process = mp.Process(
        target=celery_app.worker_main,
        args=(argv,),
        daemon=True,                      # dies with the parent process
        name=f"celery-{queue}-worker",
    )
    process.start()
    return process


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan context:
        • initialise the DB
        • launch two dedicated Celery worker **processes**
    """
    init_db()

    worker_processes: list[mp.Process] = []

    if celery_app is not None:
        # general‑purpose tasks → 4 child processes
        worker_processes.append(_spawn_celery_worker("default", 4))

        # OCR / preprocessing tasks → 1 child process
        worker_processes.append(_spawn_celery_worker("preprocess", 1))

    try:
        yield
    finally:
        # graceful shutdown
        for p in worker_processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)



app = FastAPI(lifespan=lifespan)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/user", tags=["users"])
api_router.include_router(projects.router, prefix="/project", tags=["projects"])
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
