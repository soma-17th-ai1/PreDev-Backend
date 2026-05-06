from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_optional_session, require_session
from app.models.orm import Session
from app.schemas.chat import SessionCreateRequest, SessionStartRequest
from app.schemas.common import ApiException, err_payload, ok_payload
from app.schemas.enums import Emotion, SceneId
from app.schemas.game import GameState, RecentMessage
from app.services.scene_config import get_scene_info
from app.services.session_service import (
    create_session,
    get_recent_messages,
    progress_percent,
    reset_session,
    start_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _to_game_state(session: Session) -> GameState:
    return GameState(
        player_name=session.player_name,
        affinity=session.affinity,
        chat_count=session.chat_count,
        chat_limit=session.chat_limit,
        progress=progress_percent(session.chat_count, session.chat_limit),
        current_scene_id=SceneId(session.current_scene_id),
        emotion=Emotion(session.emotion),
        is_ended=session.is_ended,
    )


@router.get("/me")
async def get_session_state(
    session: Session | None = Depends(get_optional_session),
):
    if session is None:
        return ok_payload({"has_session": False})
    return ok_payload(
        {
            "has_session": True,
            "is_started": session.is_started,
            "current_scene_id": session.current_scene_id,
            "progress": progress_percent(session.chat_count, session.chat_limit),
            "is_ended": session.is_ended,
        }
    )


@router.post("")
async def post_session(
    body: SessionCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    existing: Session | None = Depends(get_optional_session),
):
    if existing is not None:
        if not body.force_reset:
            return JSONResponse(
                status_code=409,
                content=err_payload(
                    "SESSION_ALREADY_EXISTS",
                    "이전 기록이 있습니다. 초기화하시겠습니까?",
                ),
            )
        session = await reset_session(db, existing)
    else:
        session = await create_session(db)

    _set_session_cookie(response, str(session.id))
    return ok_payload(
        {
            "session_id": str(session.id),
            "created_at": session.created_at.isoformat(),
        }
    )


@router.post("/me/start")
async def post_session_start(
    body: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(require_session),
):
    name = body.player_name.strip()
    if not name:
        raise ApiException(
            code="INVALID_INPUT", message="이름이 비어 있습니다.", status=400
        )
    session = await start_session(db, session, name)
    return ok_payload({"state": _to_game_state(session).model_dump(mode="json")})


@router.get("/me/resume")
async def get_session_resume(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(require_session),
):
    if not session.is_started:
        raise ApiException(
            code="SESSION_NOT_FOUND", message="이전 기록이 없습니다.", status=404
        )
    scene = get_scene_info(SceneId(session.current_scene_id))
    recent = await get_recent_messages(db, session.id, limit=6)
    recent_payload = [
        RecentMessage(
            role=m.role,  # type: ignore[arg-type]
            content=m.content,
            emotion=Emotion(m.emotion) if m.emotion else None,
            timestamp=m.created_at,
        ).model_dump(mode="json", exclude_none=True)
        for m in recent
    ]
    return ok_payload(
        {
            "state": _to_game_state(session).model_dump(mode="json"),
            "scene": scene.model_dump(mode="json"),
            "recent_messages": recent_payload,
        }
    )
