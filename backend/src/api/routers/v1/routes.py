from fastapi import APIRouter

from api.routers.v1.auth.router import router as auth_router
from api.routers.v1.game.router import router as game_router
from api.routers.v1.register.router import router as register_router
from api.routers.v1.system.router import router as system_router

api_router = APIRouter()
api_router.include_router(register_router)
api_router.include_router(auth_router)
api_router.include_router(game_router)
api_router.include_router(system_router)
