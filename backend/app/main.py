from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import places, health
from app.routers import routes as routes_router
from app.routers import users as users_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.version)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(users_router.router)
app.include_router(places.router)
app.include_router(routes_router.router)

