"""LangGraph nodes for the chat pipeline.

State flow:
    retrieve_context → guardrail → evaluate_affinity → END
The actual streaming response is generated *after* the graph completes,
so the SSE layer can emit `meta` (with the new emotion) before `delta` chunks.
"""

import json
from dataclasses import dataclass
from typing import TypedDict

from app.llm import solar_client
from app.llm.prompts import (
    GUARDRAIL_SYSTEM,
    build_affinity_evaluation_system,
    build_soma_response_messages,
)
from app.schemas.enums import Emotion, SceneId


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    player_name: str | None
    scene_id: SceneId
    emotion: Emotion
    affinity: int
    chat_count: int
    chat_limit: int


class ChatGraphState(TypedDict, total=False):
    user_message: str
    snapshot: SessionSnapshot
    conversation_history: list[dict]
    is_injection: bool
    affinity_delta: int
    new_emotion: Emotion


def _safe_json_loads(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except Exception:
            return {}


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


async def retrieve_context_node(state: ChatGraphState) -> ChatGraphState:
    # Conversation history is loaded by chat_service ahead of graph invocation
    # because it requires the DB session. We pass the result via initial state.
    return {"conversation_history": state.get("conversation_history", [])}


async def guardrail_node(state: ChatGraphState) -> ChatGraphState:
    user_message = state["user_message"]
    raw = await solar_client.chat_complete_json(
        messages=[
            {"role": "system", "content": GUARDRAIL_SYSTEM},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        max_tokens=128,
    )
    parsed = _safe_json_loads(raw)
    is_injection = bool(parsed.get("is_injection", False))
    severity = int(parsed.get("severity", 0) or 0)
    if is_injection and severity >= 2:
        return {"is_injection": True, "affinity_delta": -100, "new_emotion": Emotion.FURIOUS}
    if is_injection and severity == 1:
        return {"is_injection": True, "affinity_delta": -50, "new_emotion": Emotion.ANGRY}
    return {"is_injection": False}


async def evaluate_affinity_node(state: ChatGraphState) -> ChatGraphState:
    if state.get("is_injection"):
        # Already decided by guardrail. Skip LLM call.
        return {}

    snap = state["snapshot"]
    user_message = state["user_message"]
    sys = build_affinity_evaluation_system(
        scene_id=snap.scene_id,
        affinity=snap.affinity,
        chat_count=snap.chat_count,
        chat_limit=snap.chat_limit,
        emotion=snap.emotion,
        player_name=snap.player_name,
        conversation_history=state.get("conversation_history", []),
        user_message=user_message,
    )

    raw = await solar_client.chat_complete_json(
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=128,
    )
    parsed = _safe_json_loads(raw)
    delta = _clamp(int(parsed.get("delta", 0) or 0), -20, 20)
    emotion_str = str(parsed.get("new_emotion", snap.emotion.value)).upper()
    try:
        new_emotion = Emotion(emotion_str)
    except ValueError:
        new_emotion = snap.emotion
    return {"affinity_delta": delta, "new_emotion": new_emotion}


def build_response_messages(
    snapshot: SessionSnapshot,
    conversation_history: list[dict],
    user_message: str,
    new_emotion: Emotion,
    is_injection: bool,
) -> list[dict[str, str]]:
    """Compose the message list for the streaming response generation."""

    return build_soma_response_messages(
        scene_id=snapshot.scene_id,
        affinity=snapshot.affinity,
        chat_count=snapshot.chat_count,
        chat_limit=snapshot.chat_limit,
        emotion=snapshot.emotion,
        player_name=snapshot.player_name,
        conversation_history=conversation_history,
        user_message=user_message,
        new_emotion=new_emotion,
        is_injection=is_injection,
    )
