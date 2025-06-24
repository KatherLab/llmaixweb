from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .db.session import init_db
from .routers.v1.endpoints import auth, users, projects
from llmaix.__version__ import __version__

app = FastAPI()

init_db()


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

@app.get("/version")
async def version():
    return {"version": __version__, "description": "LLMAIx (v2) backend API"}

@app.get("/api/v1/version")
async def version():
    return {"version": __version__, "description": "LLMAIx (v2) backend API"}