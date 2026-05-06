from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.deps import require_session
from app.models.orm import Message, Session
from app.schemas.chat import ChatRequest
from app.schemas.common import ApiException, ok_payload
from app.schemas.enums import Emotion, MessageRole, SceneId
from app.schemas.game import HistoryMessage
from app.services.chat_service import stream_chat
from app.services.suggestion_service import get_suggestions

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def post_chat(
    body: ChatRequest,
    session: Session = Depends(require_session),
):
    message = body.message.strip()
    if not message:
        raise ApiException(
            code="INVALID_INPUT", message="메시지가 비어 있습니다.", status=400
        )
    if session.is_ended:
        raise ApiException(
            code="GAME_ALREADY_ENDED",
            message="게임이 이미 종료되었습니다.",
            status=409,
        )
    if not session.is_started:
        raise ApiException(
            code="SESSION_REQUIRED",
            message="게임이 시작되지 않았습니다.",
            status=401,
        )
    return EventSourceResponse(stream_chat(session, message))


@router.get("/chat/suggestions")
async def get_chat_suggestions(
    session: Session = Depends(require_session),
):
    if session.is_ended:
        raise ApiException(
            code="GAME_ALREADY_ENDED",
            message="게임이 이미 종료되었습니다.",
            status=409,
        )
    items = await get_suggestions(session)
    return ok_payload({"suggestions": items})


@router.get("/chat/history")
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(require_session),
    limit: int = Query(default=50, ge=1, le=100),
    before: str | None = Query(default=None),
):
    stmt = select(Message).where(Message.session_id == session.id)
    if before:
        anchor = await db.get(Message, before)
        if anchor is not None:
            stmt = stmt.where(Message.created_at < anchor.created_at)
    stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()  # oldest first

    messages = [
        HistoryMessage(
            message_id=str(m.id),
            role=MessageRole(m.role),
            content=m.content,
            emotion=Emotion(m.emotion) if m.emotion else None,
            scene_id=SceneId(m.scene_id) if m.scene_id else None,
            timestamp=m.created_at,
        ).model_dump(mode="json", exclude_none=True)
        for m in rows
    ]
    next_cursor = str(rows[0].id) if rows else None
    return ok_payload({"messages": messages, "next_cursor": next_cursor})
