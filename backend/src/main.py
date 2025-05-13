from fastapi import Depends, FastAPI

from .core.security import get_admin_user
from .db.session import init_db
from .internal import admin
from .routers.v1.api import api_router

app = FastAPI()

init_db()

app.include_router(
    api_router,
    prefix="/api/v1",
    tags=["api"],
)
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)],
    responses={418: {"description": "I'm a teapot"}},
)


@app.get("/")
async def root():
    return {"message": "Hello, hello!"}
