from fastapi import FastAPI, APIRouter
from .db.session import init_db
from .routers.v1.endpoints import auth, users, projects

app = FastAPI()

init_db()


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/user", tags=["users"])
api_router.include_router(projects.router, prefix="/project", tags=["projects"])

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Hello, hello!"}
