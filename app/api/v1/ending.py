from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_session
from app.models.orm import Session
from app.schemas.common import ApiException, ok_payload
from app.services.ending_service import build_ending_payload

router = APIRouter(prefix="/game", tags=["ending"])


@router.get("/ending")
async def get_ending(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(require_session),
):
    if not session.is_ended:
        raise ApiException(
            code="GAME_NOT_ENDED",
            message="아직 게임이 진행 중입니다.",
            status=425,
        )
    payload = await build_ending_payload(db, session)
    return ok_payload(payload.model_dump(mode="json"))
