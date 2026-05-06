from fastapi import APIRouter

from app.api.v1 import chat, ending, health, scenes, sessions

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(sessions.router)
api_v1.include_router(chat.router)
api_v1.include_router(scenes.router)
api_v1.include_router(ending.router)
api_v1.include_router(health.router)
