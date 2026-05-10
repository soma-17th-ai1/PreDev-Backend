"""Scene configuration: thresholds (§1.6.1), titles, and intro_dialogues (§4.1).

Pure data + helpers. No DB access, no LLM.
"""

from app.schemas.enums import Emotion, SceneId
from app.schemas.game import IntroDialogueCharacter, IntroDialogueNarration, SceneInfo

# Order matters: ascending chat_count threshold for entry.
# §1.6.1 — chat_count threshold to ENTER each story scene.
SCENE_ORDER: list[tuple[SceneId, int]] = [
    (SceneId.SCENE_INTRO, 0),
    (SceneId.SCENE_FIRST_MEET, 0),
    (SceneId.SCENE_PROJECT_PLAN_EVALUATION, 5),
    (SceneId.SCENE_LAUNCH_CEREMONY, 8),
    (SceneId.SCENE_MID_EVALUATION, 11),
    (SceneId.SCENE_DEEP_DEV, 16),
    (SceneId.SCENE_FINAL_EVALUATION, 19),
    (SceneId.SCENE_GRADUATION_BUSAN, 22),
]

SCENE_THRESHOLDS: dict[SceneId, int] = dict(SCENE_ORDER)


SCENE_TITLES: dict[SceneId, str] = {
    SceneId.SCENE_INTRO: "인트로",
    SceneId.SCENE_FIRST_MEET: "S룸 첫 만남",
    SceneId.SCENE_PROJECT_PLAN_EVALUATION: "기획 심의",
    SceneId.SCENE_LAUNCH_CEREMONY: "발대식",
    SceneId.SCENE_MID_EVALUATION: "중간평가",
    SceneId.SCENE_DEEP_DEV: "새벽 개발",
    SceneId.SCENE_FINAL_EVALUATION: "최종평가",
    SceneId.SCENE_GRADUATION_BUSAN: "수료식 부산",
    SceneId.SCENE_ENDING_INSTANT_BAD: "즉시 베드엔딩",
    SceneId.SCENE_ENDING_BAD: "배드엔딩",
    SceneId.SCENE_ENDING_NORMAL_NO_CONTACT: "노멀엔딩 - 연락 끊김",
    SceneId.SCENE_ENDING_NORMAL_CONTACT: "노멀엔딩 - 가끔 연락",
    SceneId.SCENE_ENDING_HAPPY: "해피엔딩",
    SceneId.SCENE_ENDING_MARRIAGE: "결혼 해피엔딩",
}


def _n(text: str) -> IntroDialogueNarration:
    return IntroDialogueNarration(text=text)


def _c(emotion: Emotion, text: str, name: str = "이세라") -> IntroDialogueCharacter:
    return IntroDialogueCharacter(name=name, emotion=emotion, text=text)


# Static intro_dialogues — LLM은 사용하지 않는다 (§4.1, §1.6.1).
SCENE_INTROS: dict[SceneId, list] = {
    SceneId.SCENE_INTRO: [
        _n("Software Maestro 16기 첫 출근 날."),
        _n("S룸 문 앞에서 가볍게 숨을 골랐다."),
    ],
    SceneId.SCENE_FIRST_MEET: [
        _n("S룸 안쪽에 자리잡은 한 명이 천천히 고개를 들었다."),
        _c(Emotion.NEUTRAL, "..처음 보는 얼굴이네요. 같은 기수?"),
    ],
    SceneId.SCENE_PROJECT_PLAN_EVALUATION: [
        _n("기획 심의 전날, 슬라이드를 마지막으로 점검 중이다."),
        _c(Emotion.NEUTRAL, "발표 흐름은 좀 봤어요?"),
    ],
    SceneId.SCENE_LAUNCH_CEREMONY: [
        _n("발대식 행사장의 조명이 환했다."),
        _c(Emotion.SHY, "..사람 많으니까 좀 어색하네요."),
    ],
    SceneId.SCENE_MID_EVALUATION: [
        _n("중간평가가 코 앞이다. 지난 몇 주가 빠르게 지나갔다."),
        _c(Emotion.NEUTRAL, "데모 영상 한 번만 같이 봐줄래요?"),
    ],
    SceneId.SCENE_DEEP_DEV: [
        _n("워크숍 둘째 날이 밝았다."),
        _c(Emotion.NEUTRAL, "어, 일찍 오셨네요?"),
    ],
    SceneId.SCENE_FINAL_EVALUATION: [
        _n("최종평가일. 제출 직전의 정적이 무겁다."),
        _c(Emotion.EXCITED, "..드디어 끝나네요. 마지막까지 가보죠."),
    ],
    SceneId.SCENE_GRADUATION_BUSAN: [
        _n("수료식이 끝나고, 일행은 부산으로 향했다."),
        _c(Emotion.HAPPY, "바다 보면서 회 한 접시는 국룰이죠."),
    ],
    SceneId.SCENE_ENDING_INSTANT_BAD: [
        _n("그 날 이후, 세라는 단톡방에서 조용히 빠져나갔다."),
    ],
    SceneId.SCENE_ENDING_BAD: [
        _n("수료 이후, 둘 사이에는 어색한 침묵만 남았다."),
    ],
    SceneId.SCENE_ENDING_NORMAL_NO_CONTACT: [
        _n("연락은 자연스럽게 끊겼다. 가끔 SNS에서 안부를 짐작할 뿐이었다."),
    ],
    SceneId.SCENE_ENDING_NORMAL_CONTACT: [
        _n("이따금 짧은 메시지가 오갔다. 그 정도의 거리감이 편했다."),
    ],
    SceneId.SCENE_ENDING_HAPPY: [
        _n("수료 이후에도 둘은 자주 마주쳤다. 묘한 긴장감이 좋았다."),
    ],
    SceneId.SCENE_ENDING_MARRIAGE: [
        _n("몇 해의 시간이 흘렀다. 어느 봄날, 둘은 같은 성을 쓰게 되었다."),
    ],
}


def get_scene_info(scene_id: SceneId) -> SceneInfo:
    return SceneInfo(
        scene_id=scene_id,
        title=SCENE_TITLES[scene_id],
        intro_dialogues=list(SCENE_INTROS.get(scene_id, [])),
    )


def next_scene_for_chat_count(chat_count: int) -> SceneId:
    """Return the latest story scene whose threshold is <= chat_count."""

    current = SceneId.SCENE_INTRO
    for scene_id, threshold in SCENE_ORDER:
        if chat_count >= threshold:
            current = scene_id
        else:
            break
    return current
