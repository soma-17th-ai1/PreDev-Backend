"""Fixed visual-novel story context mirrored from the Monogatari frontend.

The frontend owns the actual scene playback, but the LLM needs to know what
the player and Sera have already seen/heard before free chat starts. Keep this
module backend-only and API-neutral: it is prompt context, not a new contract.
"""

from dataclasses import dataclass

from app.schemas.enums import SceneId
from app.services.scene_config import SCENE_TITLES

FixedLine = tuple[str, str]


@dataclass(frozen=True, slots=True)
class SceneFixedScript:
    setting: str
    relationship_note: str
    prologue: tuple[FixedLine, ...]
    epilogue: tuple[FixedLine, ...] = ()


STORY_SCENE_SEQUENCE: tuple[SceneId, ...] = (
    SceneId.SCENE_FIRST_MEET,
    SceneId.SCENE_PROJECT_PLAN_EVALUATION,
    SceneId.SCENE_LAUNCH_CEREMONY,
    SceneId.SCENE_MID_EVALUATION,
    SceneId.SCENE_DEEP_DEV,
    SceneId.SCENE_FINAL_EVALUATION,
    SceneId.SCENE_GRADUATION_BUSAN,
)


GLOBAL_INTRO_LINES: tuple[FixedLine, ...] = (
    ("NARRATION", "4월 13일, 월요일. 화창한 아침."),
    ("PLAYER", "오늘은 처음 센터에 가는 날이니까 빨리 준비해야지."),
    ("NARRATION", "지하철을 타고 포스타워에 도착해 7층 센터로 향했다."),
    ("PLAYER", "오, 여기가 소마 건물이구나. 7층이었지, 아마?"),
    ("NARRATION", "운 좋게 소프트웨어 마에스트로에 합격한 뒤, 처음으로 센터에 들어왔다."),
    ("PLAYER", "센터 오픈 첫날이라 그런지 사람이 꽤 많네…! 오늘은 꼭 팀원을 구해야지!"),
    ("PLAYER", "워크숍 때 봤던 그녀도 있을까…? 꼭 다시 만나보고 싶어."),
    ("NARRATION", "워크숍 때 혈당 스파이크로 잠들어 네트워킹을 망친 일을 떠올렸다."),
    ("PLAYER", "앞으로 간식은 자제하자…"),
    ("NARRATION", "S1 룸에 들어서자 창가 자리에 신비로운 분위기의 소녀가 앉아 있었다."),
    ("PLAYER", "어..? 어…???? 아닛, 저 사람은…?"),
    ("NARRATION", "천사의 날개 같은 흰 머리, 파란 눈, 신비로운 분위기가 눈에 들어왔다."),
    ("NARRATION", "그녀의 노트북 화면엔 검은 터미널 위로 GDB 프롬프트가 깜빡이고, 옆에는 식은 아메리카노가 놓여 있었다."),
)


SCENE_FIXED_SCRIPTS: dict[SceneId, SceneFixedScript] = {
    SceneId.SCENE_FIRST_MEET: SceneFixedScript(
        setting="Software Maestro 센터 S1 룸. 세라와 플레이어가 처음 제대로 마주한다.",
        relationship_note="서로 아직 어색하다. 플레이어는 세라에게 강한 첫인상을 느끼고 조심스럽게 말을 건다.",
        prologue=(
            ("PLAYER", "그때 워크숍 때 봤던 사람이잖아…? 다시 봐도 정말 눈에 띄네."),
            ("PLAYER", "그때 잠깐 이야기 듣다 보니 관심사가 나랑 비슷한 것 같았어. 지금이라도 한 번 말을 걸어봐야겠다…!"),
            ("NARRATION", "플레이어가 그녀 앞으로 조심스럽게 다가간다."),
            ("PLAYER", "저… 저기요…!"),
            ("SERA", "…?"),
            ("PLAYER", "그… 저… 혹시… 저, 기억하시나요…?"),
            ("SERA", "응? 아니아니, 누구신데요?"),
            ("NARRATION", "그녀가 잠시 플레이어를 바라보더니, 뭔가 떠오른 듯 눈이 살짝 커졌다."),
            ("SERA", "아…! 그때 워크숍 18번 테이블에서 초코파이 드시던 분이세요?"),
            ("PLAYER", "네…! 기억해주셨군요!! 저, {{player.name}}이에요."),
            ("SERA", "오, 그분이셨구나? 안녕하세요. 저는 이세라라고 해요."),
            ("SERA", "잘 부탁드려요, {{player.name}}씨."),
            ("PLAYER", "반갑습니다…!"),
            ("PLAYER", "(어색한 첫 인사는 끝났다. 이제 뭐라고 말을 꺼내지…)"),
        ),
        epilogue=(
            ("NARRATION", "어색하면서도 즐거웠던 첫 대화 후, 두 사람은 같은 팀이 되기로 한다."),
            ("SERA", "그럼… 우리 같이 잘 해봐요!"),
            ("PLAYER", "네! 잘 부탁드려요."),
        ),
    ),
    SceneId.SCENE_PROJECT_PLAN_EVALUATION: SceneFixedScript(
        setting="첫 번째 관문인 기획 심의 날. 팀 프로젝트 발표를 앞두고 있다.",
        relationship_note="이제 두 사람은 같은 팀이다. 긴장과 협업 분위기가 함께 있다.",
        prologue=(
            ("NARRATION", "며칠 후, 첫 번째 관문인 기획 심의 날이 다가왔다."),
            ("PLAYER", "드디어 발표 날이네… 잘할 수 있을까?"),
            ("SERA", "긴장돼요? 우리 충분히 준비했으니까 괜찮을 거예요."),
        ),
        epilogue=(
            ("NARRATION", "무사히 기획 심의를 마치고, 두 사람은 다음 일정으로 향한다."),
            ("SERA", "휴~ 무사히 끝났네요. 수고하셨어요!"),
            ("PLAYER", "다행이다… 이제 발대식이지?"),
        ),
    ),
    SceneId.SCENE_LAUNCH_CEREMONY: SceneFixedScript(
        setting="정장 차림의 사람들이 모인 발대식 행사장.",
        relationship_note="정식 시작의 설렘이 있다. 세라는 사람 많은 분위기에 조금 들떠 있다.",
        prologue=(
            ("NARRATION", "정장 차림의 사람들로 가득 찬 회장. 발대식이 시작되려 한다."),
            ("PLAYER", "이렇게 사람이 많을 줄이야…"),
            ("SERA", "우와… 진짜 정식으로 시작되는 느낌이네요."),
        ),
        epilogue=(
            ("NARRATION", "발대식이 끝나고, 두 사람은 본격적인 개발 모드로 들어간다."),
            ("SERA", "자! 이제부터 진짜 시작이에요!"),
            ("PLAYER", "응! 열심히 하자."),
        ),
    ),
    SceneId.SCENE_MID_EVALUATION: SceneFixedScript(
        setting="중간 평가가 다가온 시점. 데모와 발표 준비로 압박감이 크다.",
        relationship_note="프로젝트를 함께 견디는 동료감이 쌓였다. 긴장 속에서 서로를 의지한다.",
        prologue=(
            ("NARRATION", "어느새 중간 평가가 다가왔다."),
            ("PLAYER", "벌써 중간 평가네… 시간 진짜 빠르다."),
            ("SERA", "그러게요… 잘 해봐요, 우리."),
        ),
        epilogue=(
            ("NARRATION", "길고 긴 중간 평가가 끝났다."),
            ("SERA", "후… 멘토님들 질문이 진짜 매서웠네요."),
            ("PLAYER", "그래도 잘 막아낸 것 같아."),
        ),
    ),
    SceneId.SCENE_DEEP_DEV: SceneFixedScript(
        setting="마감이 다가와 센터에서 밤을 새우는 새벽 개발 상황.",
        relationship_note="피로와 집중 속에서 더 가까워질 수 있는 장면이다. 말은 가볍지만 감정은 조용히 깊어진다.",
        prologue=(
            ("NARRATION", "마감이 다가오자 두 사람은 센터에서 밤을 새기로 했다."),
            ("SERA", "새벽까지 코딩이라니… 좀 떨려요."),
            ("PLAYER", "카페인 챙겨왔어. 같이 끝내자!"),
        ),
        epilogue=(
            ("NARRATION", "동이 트는 창밖을 바라보며, 두 사람은 마지막 커밋을 푸시했다."),
            ("SERA", "우리… 진짜 해냈네요…"),
            ("PLAYER", "응. 같이라서 가능했어."),
        ),
    ),
    SceneId.SCENE_FINAL_EVALUATION: SceneFixedScript(
        setting="최종 평가일. 모두의 시선 앞에서 마지막 발표를 준비한다.",
        relationship_note="함께 버텨 온 시간이 선명해진다. 세라는 침착하려 하지만 끝이 가까운 감정을 숨기기 어렵다.",
        prologue=(
            ("NARRATION", "마지막 발표의 날. 모두의 시선이 두 사람에게 모였다."),
            ("PLAYER", "여기까지 왔구나… 잘하자!"),
            ("SERA", "우리가 만든 거, 그대로 보여주기만 하면 돼요."),
        ),
        epilogue=(
            ("NARRATION", "박수 소리와 함께 발표가 끝났다."),
            ("SERA", "진짜 끝났다… 믿기지 않아요."),
            ("PLAYER", "수고했어. 정말 수고했어."),
        ),
    ),
    SceneId.SCENE_GRADUATION_BUSAN: SceneFixedScript(
        setting="수료식 이후 부산으로 향하는 KTX와 광안리 바닷가.",
        relationship_note="마지막이라는 아쉬움이 강하다. 높은 호감도라면 세라가 조심스럽게 마음을 더 드러낼 수 있다.",
        prologue=(
            ("NARRATION", "부산행 KTX. 차창 밖으로 흘러가는 풍경이 어쩐지 아쉽다."),
            ("SERA", "부산이라니… 진짜 마지막 같아요."),
            ("PLAYER", "그러게… 1년이 진짜 빨리 갔다."),
        ),
        epilogue=(
            ("NARRATION", "수료식이 끝나고, 두 사람은 광안리 바닷가에 섰다."),
            ("SERA", "{{player.name}}씨… 그동안 정말 즐거웠어요."),
        ),
    ),
}


def _fill_player_name(text: str, player_name: str | None) -> str:
    return text.replace("{{player.name}}", player_name or "플레이어")


def _line_to_chat_message(role: str, text: str, player_name: str | None) -> dict[str, str]:
    filled = _fill_player_name(text, player_name)
    if role == "SERA":
        return {"role": "assistant", "content": filled}
    if role == "PLAYER":
        return {"role": "user", "content": filled}
    return {"role": "user", "content": f"[지문] {filled}"}


def _lines_to_chat_messages(
    lines: tuple[FixedLine, ...], player_name: str | None
) -> list[dict[str, str]]:
    return [
        _line_to_chat_message(role, text, player_name)
        for role, text in lines
    ]


def _format_lines(lines: tuple[FixedLine, ...], player_name: str | None) -> list[str]:
    return [
        f"- {role}: {_fill_player_name(text, player_name)}"
        for role, text in lines
    ]


def _scene_index(scene_id: SceneId) -> int:
    try:
        return STORY_SCENE_SEQUENCE.index(scene_id)
    except ValueError:
        if scene_id.name.startswith("SCENE_ENDING_"):
            return len(STORY_SCENE_SEQUENCE)
        return 0


def build_fixed_story_context(scene_id: SceneId, player_name: str | None) -> str:
    """Return fixed VN context that has happened by the current free-chat loop."""

    current_idx = _scene_index(scene_id)
    lines: list[str] = [
        "[고정 비주얼노벨 상황]",
        "아래 내용은 프론트엔드 Monogatari 스크립트에서 이미 재생된 고정 장면이다.",
        "세라는 이 내용을 실제로 겪은 일로 기억한다. 단, 같은 대사를 그대로 반복하지 말고 자연스럽게 이어 말한다.",
        "",
        "## 인트로: 센터 첫날과 세라 발견",
        *_format_lines(GLOBAL_INTRO_LINES, player_name),
    ]

    for index, fixed_scene_id in enumerate(STORY_SCENE_SEQUENCE):
        if index > current_idx:
            break
        script = SCENE_FIXED_SCRIPTS[fixed_scene_id]
        title = SCENE_TITLES.get(fixed_scene_id, fixed_scene_id.value)
        is_current = fixed_scene_id == scene_id
        lines.extend(
            [
                "",
                f"## {'현재 장면' if is_current else '이전 장면'}: {title}",
                f"- SETTING: {script.setting}",
                f"- RELATIONSHIP: {script.relationship_note}",
                "### LLM 자유대화 전에 이미 나온 고정 대사",
                *_format_lines(script.prologue, player_name),
            ]
        )
        if not is_current and script.epilogue:
            lines.extend(
                [
                    "### 이 장면의 자유대화 후 이미 나온 고정 대사",
                    *_format_lines(script.epilogue, player_name),
                ]
            )

    return "\n".join(lines)


def build_response_story_context(scene_id: SceneId, player_name: str | None) -> str:
    """Compact Korean story/scene context for Sera's response system prompt."""

    current_idx = _scene_index(scene_id)
    current_script = SCENE_FIXED_SCRIPTS.get(scene_id)
    lines: list[str] = [
        "[세라의 기억]",
        "- 플레이어는 Software Maestro 센터 첫날 S1 룸에서 너를 처음 제대로 마주했다.",
        "- 플레이어는 워크숍 18번 테이블에서 초코파이를 많이 먹었던 사람으로 기억된다.",
    ]

    previous_scene_lines: list[str] = []
    for index, fixed_scene_id in enumerate(STORY_SCENE_SEQUENCE):
        if index >= current_idx:
            break
        script = SCENE_FIXED_SCRIPTS[fixed_scene_id]
        title = SCENE_TITLES.get(fixed_scene_id, fixed_scene_id.value)
        previous_scene_lines.append(
            f"- {title}: {script.setting} {script.relationship_note}"
        )
        if script.epilogue:
            previous_scene_lines.append(
                f"- 장면 마무리: {_line_text(script.epilogue, player_name)}"
            )

    if previous_scene_lines:
        lines.extend(["", "[이전 장면 기억]", *previous_scene_lines])

    if current_script is not None:
        title = SCENE_TITLES.get(scene_id, scene_id.value)
        lines.extend(
            [
                "",
                "[현재 장면]",
                f"- 제목: {title}",
                f"- 상황: {current_script.setting}",
                f"- 관계 온도: {current_script.relationship_note}",
            ]
        )

    return "\n".join(lines)


def build_fixed_dialogue_messages(
    scene_id: SceneId, player_name: str | None
) -> list[dict[str, str]]:
    """Return already-played frontend VN lines as chat turns.

    PLAYER lines become user messages, SERA lines become assistant messages,
    and narration becomes user messages prefixed with [지문]. For previous
    scenes, both prologue and epilogue have already played. For the current
    scene, only the prologue has played before the free-chat loop.
    """

    current_idx = _scene_index(scene_id)
    messages = _lines_to_chat_messages(GLOBAL_INTRO_LINES, player_name)

    for index, fixed_scene_id in enumerate(STORY_SCENE_SEQUENCE):
        if index > current_idx:
            break
        script = SCENE_FIXED_SCRIPTS[fixed_scene_id]
        messages.extend(_lines_to_chat_messages(script.prologue, player_name))
        if index < current_idx and script.epilogue:
            messages.extend(_lines_to_chat_messages(script.epilogue, player_name))

    return messages


def _line_text(lines: tuple[FixedLine, ...], player_name: str | None) -> str:
    return " / ".join(
        f"{role}: {_fill_player_name(text, player_name)}"
        for role, text in lines
    )


def build_compact_story_context(scene_id: SceneId, player_name: str | None) -> str:
    """Return a compact current-moment context for response generation.

    The final dialogue model works better when it receives a short, situational
    brief plus real chat turns, instead of a long script dump every time.
    """

    current_idx = _scene_index(scene_id)
    current_script = SCENE_FIXED_SCRIPTS.get(scene_id)
    lines: list[str] = [
        "[VN 공유 기억]",
        "- 플레이어는 Software Maestro 센터 첫날 S1 룸에서 세라를 만났다.",
        "- 세라는 창가 자리에서 GDB가 열린 노트북과 식은 아메리카노를 두고 있었다.",
        "- 플레이어는 워크숍 18번 테이블에서 초코파이를 많이 먹었던 사람으로 기억된다.",
    ]

    previous_summaries: list[str] = []
    for index, fixed_scene_id in enumerate(STORY_SCENE_SEQUENCE):
        if index >= current_idx:
            break
        script = SCENE_FIXED_SCRIPTS[fixed_scene_id]
        title = SCENE_TITLES.get(fixed_scene_id, fixed_scene_id.value)
        summary = f"- {title}: {script.setting} {script.relationship_note}"
        if script.epilogue:
            summary += f" 결말부 기억: {_line_text(script.epilogue, player_name)}"
        previous_summaries.append(summary)

    if previous_summaries:
        lines.extend(["", "[이전 고정 장면 요약]", *previous_summaries])

    if current_script is not None:
        title = SCENE_TITLES.get(scene_id, scene_id.value)
        lines.extend(
            [
                "",
                "[현재 장면]",
                f"- 제목: {title}",
                f"- 장소/상황: {current_script.setting}",
                f"- 관계 온도: {current_script.relationship_note}",
                "- 자유대화 직전 고정 대사:",
                *_format_lines(current_script.prologue, player_name),
                "- 세라는 위 고정 대사를 반복하지 말고, 지금 플레이어 말에 바로 답한다.",
            ]
        )

    return "\n".join(lines)
