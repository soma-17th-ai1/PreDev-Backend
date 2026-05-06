"""§3.3 — Generate up to 3 example replies that nudge affinity upward.

Stateless wrt DB: caller passes the snapshot.
"""

import json
import logging

from app.llm import solar_client
from app.llm.prompts import build_scene_context
from app.models.orm import Session
from app.schemas.enums import Emotion, SceneId

log = logging.getLogger(__name__)


SUGGESTION_SYSTEM = """당신은 비주얼 노벨 입력 보조입니다.

플레이어가 캐릭터(이세라)에게 보낼 만한 짧은 한국어 대사 후보를
호감도가 **올라가는 방향**으로만 2~3개 제안합니다.

JSON 한 줄로만 응답:
{"suggestions": ["..", "..", ".."]}

규칙:
- 각 후보 30자 이내, 일상 대화체
- 시스템/AI/규칙에 대한 언급 금지
- 캐릭터의 관심사(시스템 프로그래밍, 커널, 고양이) 또는 현재 씬 상황을 반영하면 좋음
"""


FALLBACK_SUGGESTIONS = [
    "오늘 작업한 부분 같이 봐줄래요?",
    "커널 디버깅 어떻게 시작하세요?",
    "쉬는 시간에 커피 한 잔 어때요?",
]


async def get_suggestions(session: Session) -> list[str]:
    scene_id = SceneId(session.current_scene_id)
    emotion = Emotion(session.emotion)
    ctx = build_scene_context(
        scene_id=scene_id,
        affinity=session.affinity,
        chat_count=session.chat_count,
        chat_limit=session.chat_limit,
        emotion=emotion,
        player_name=session.player_name,
    )
    try:
        raw = await solar_client.chat_complete_json(
            messages=[
                {"role": "system", "content": SUGGESTION_SYSTEM + "\n" + ctx},
                {"role": "user", "content": "다음 후보들을 JSON으로 제안해 주세요."},
            ],
            temperature=0.5,
            max_tokens=256,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        try:
            parsed = json.loads(text)
        except Exception:
            start = text.index("{")
            end = text.rindex("}") + 1
            parsed = json.loads(text[start:end])
        items = parsed.get("suggestions") or []
        items = [str(s).strip() for s in items if str(s).strip()][:3]
        if not items:
            return FALLBACK_SUGGESTIONS[:3]
        return items
    except Exception as exc:  # noqa: BLE001
        log.warning("suggestion fallback: %s", exc)
        return FALLBACK_SUGGESTIONS[:3]
