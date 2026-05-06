from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.llm import solar_client
from app.schemas.common import ok_payload

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = f"error: {exc.__class__.__name__}"

    llm_ok = "ok" if await solar_client.health_check() else "unavailable"

    overall = "healthy" if db_ok == "ok" and llm_ok == "ok" else "degraded"
    return ok_payload({"status": overall, "llm_provider": llm_ok, "db": db_ok})
