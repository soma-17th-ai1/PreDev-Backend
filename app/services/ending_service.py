"""§5.1 ending content. Generates a narrative once via LLM and caches it."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import solar_client
from app.llm.prompts import SOMA_PERSONA
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


async def _generate_narrative(
    *, ending_id: EndingId, player_name: str | None, final_affinity: int
) -> str:
    name = player_name or "주인공"
    sys = (
        SOMA_PERSONA
        + "\n\n"
        + "이제 게임이 종료되었습니다. 아래 엔딩 종류와 호감도를 반영해, "
        + "소마(이세라)와 주인공의 결말을 한국어 서사 문체로 4~6문장 정도로 자연스럽게 묘사하세요. "
        + "대사가 들어가도 좋지만 1인칭이 아닌 3인칭 서사 위주로 쓰세요."
    )
    user = (
        f"엔딩: {ending_id.value} ({_ENDING_TITLES[ending_id]})\n"
        f"최종 호감도: {final_affinity}\n"
        f"플레이어 이름: {name}"
    )
    try:
        return (
            await solar_client.chat_complete_json(
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": user},
                ],
                temperature=0.6,
                max_tokens=512,
            )
        ).strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("ending narrative fallback: %s", exc)
        return f"{name}와 이세라의 이야기는 {_ENDING_TITLES[ending_id]}로 끝을 맺었다."


async def build_ending_payload(db: AsyncSession, session: Session) -> EndingPayload:
    scene_id = SceneId(session.current_scene_id)
    ending_id = _ending_id_for_scene(scene_id)

    if not session.ending_narrative:
        narrative = await _generate_narrative(
            ending_id=ending_id,
            player_name=session.player_name,
            final_affinity=session.affinity,
        )
        session.ending_narrative = narrative
        await db.commit()
    else:
        narrative = session.ending_narrative

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
        narrative=narrative,
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
