from fastapi import APIRouter

from app.api.v1 import chat, dev, ending, health, scenes, sessions
from app.config import get_settings

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(sessions.router)
if get_settings().dev_mode:
    api_v1.include_router(dev.router)
api_v1.include_router(chat.router)
api_v1.include_router(scenes.router)
api_v1.include_router(ending.router)
api_v1.include_router(health.router)
