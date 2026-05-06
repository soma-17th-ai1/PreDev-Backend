from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.orm import Message, MessageEmbedding, Session, TriggeredEvent
from app.schemas.enums import Emotion, SceneId


async def get_session(db: AsyncSession, session_id: UUID) -> Session | None:
    return await db.get(Session, session_id)


async def get_session_with_events(db: AsyncSession, session_id: UUID) -> Session | None:
    stmt = (
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.triggered_events))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_session(db: AsyncSession) -> Session:
    settings = get_settings()
    session = Session(
        chat_limit=settings.chat_limit_default,
        current_scene_id=SceneId.SCENE_INTRO.value,
        emotion=Emotion.NEUTRAL.value,
    )
    db.add(session)
    await db.flush()
    await db.commit()
    await db.refresh(session)
    return session


async def reset_session(db: AsyncSession, session: Session) -> Session:
    """Reset all gameplay state and delete history. Same session_id is preserved."""

    settings = get_settings()
    await db.execute(delete(MessageEmbedding).where(MessageEmbedding.session_id == session.id))
    await db.execute(delete(Message).where(Message.session_id == session.id))
    await db.execute(delete(TriggeredEvent).where(TriggeredEvent.session_id == session.id))

    session.player_name = None
    session.affinity = 0
    session.chat_count = 0
    session.chat_limit = settings.chat_limit_default
    session.current_scene_id = SceneId.SCENE_INTRO.value
    session.emotion = Emotion.NEUTRAL.value
    session.is_started = False
    session.is_ended = False
    session.max_affinity = 0
    session.min_affinity = 0
    session.ending_narrative = None
    session.last_active_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)
    return session


async def start_session(db: AsyncSession, session: Session, player_name: str) -> Session:
    session.player_name = player_name
    session.is_started = True
    session.current_scene_id = SceneId.SCENE_INTRO.value
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


async def touch_last_active(db: AsyncSession, session: Session) -> None:
    session.last_active_at = datetime.now(timezone.utc)
    await db.commit()


async def get_recent_messages(
    db: AsyncSession, session_id: UUID, limit: int = 6
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(reversed(rows))


def progress_percent(chat_count: int, chat_limit: int) -> int:
    if chat_limit <= 0:
        return 0
    return min(100, int(chat_count / chat_limit * 100))
