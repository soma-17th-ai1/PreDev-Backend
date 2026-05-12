"""§5.1 ending content."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Session, TriggeredEvent
from app.schemas.enums import (
    SCENE_TO_ENDING,
    EndingId,
    EventId,
    SceneId,
)
from app.schemas.game import EndingPayload, EndingStats
from app.services.scene_config import SCENE_TITLES

log = logging.getLogger(__name__)


_ENDING_TITLES: dict[EndingId, str] = {
    EndingId.ENDING_INSTANT_BAD: "즉시 베드엔딩",
    EndingId.ENDING_BAD: "배드엔딩",
    EndingId.ENDING_NORMAL_NO_CONTACT: "노멀엔딩 - 연락 끊김",
    EndingId.ENDING_NORMAL_CONTACT: "노멀엔딩 - 가끔 연락",
    EndingId.ENDING_HAPPY: "해피엔딩",
    EndingId.ENDING_MARRIAGE: "결혼 해피엔딩",
}


def _ending_id_for_scene(scene_id: SceneId) -> EndingId:
    if scene_id not in SCENE_TO_ENDING:
        # Defensive: should never happen because endpoint guards is_ended.
        return EndingId.ENDING_NORMAL_NO_CONTACT
    return SCENE_TO_ENDING[scene_id]


async def build_ending_payload(db: AsyncSession, session: Session) -> EndingPayload:
    scene_id = SceneId(session.current_scene_id)
    ending_id = _ending_id_for_scene(scene_id)

    stmt = select(TriggeredEvent.event_id).where(
        TriggeredEvent.session_id == session.id
    )
    fired = (await db.execute(stmt)).scalars().all()
    events_triggered: list[EventId] = []
    for raw in fired:
        try:
            events_triggered.append(EventId(raw))
        except ValueError:
            continue

    return EndingPayload(
        ending_id=ending_id,
        title=_ENDING_TITLES[ending_id],
        final_affinity=session.affinity,
        stats=EndingStats(
            total_chats=session.chat_count,
            max_affinity=session.max_affinity,
            min_affinity=session.min_affinity,
            events_triggered=events_triggered,
        ),
    )


# re-export for unit tests / callers that want to know titles.
ENDING_TITLES = _ENDING_TITLES
SCENE_TITLES = SCENE_TITLES  # noqa: F811
