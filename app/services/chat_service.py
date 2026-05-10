"""SSE orchestration for POST /api/v1/chat (§3.2).

Flow:
    1. persist USER message + best-effort embedding
    2. run LangGraph → guardrail + affinity_delta + new_emotion
    3. compute new affinity / chat_count / scene transitions / events
    4. emit SSE: meta → delta×N → state → event_trigger? → scene_transition? → end
    5. persist ASSISTANT message + best-effort embedding
    6. commit final session state and triggered events
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.llm.graph import get_graph
from app.llm.nodes import SessionSnapshot, build_response_messages
from app.llm.solar_client import chat_stream
from app.models.orm import Message, Session, TriggeredEvent
from app.schemas.chat import (
    SseDeltaPayload,
    SseEndPayload,
    SseErrorPayload,
    SseEventTriggerPayload,
    SseMetaPayload,
    SseSceneTransitionPayload,
    SseStatePayload,
)
from app.schemas.enums import (
    ENDING_SCENE_IDS,
    Emotion,
    MessageRole,
    SceneId,
)
from app.services import vector_store
from app.services.session_service import progress_percent
from app.services.trigger_engine import evaluate_triggers
from app.utils.sse import to_event

log = logging.getLogger(__name__)

CHUNK_FLUSH_AT_CHARS = 12
SENTENCE_BOUNDARIES = ".!?。！？\n"


async def _persist_message(
    db: AsyncSession,
    *,
    session_id,
    role: MessageRole,
    content: str,
    emotion: Emotion | None = None,
    scene_id: SceneId | None = None,
    affinity_after: int | None = None,
) -> Message:
    msg = Message(
        session_id=session_id,
        role=role.value,
        content=content,
        emotion=emotion.value if emotion else None,
        scene_id=scene_id.value if scene_id else None,
        affinity_after=affinity_after,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def _embed_silently(
    db: AsyncSession, *, message_id, session_id, content: str
) -> None:
    try:
        await vector_store.store_embedding(
            db, message_id=message_id, session_id=session_id, content=content
        )
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        log.warning("embedding skipped: %s", exc)


def _semantic_chunks(buffer: str) -> tuple[str, str]:
    """Return (flushable_chunk, remaining_buffer).

    Flush when:
    - buffer contains a sentence boundary, or
    - buffer length >= CHUNK_FLUSH_AT_CHARS
    """

    if len(buffer) >= CHUNK_FLUSH_AT_CHARS:
        # Prefer sentence boundary if any in this window.
        for i in range(len(buffer) - 1, -1, -1):
            if buffer[i] in SENTENCE_BOUNDARIES:
                return buffer[: i + 1], buffer[i + 1 :]
        return buffer, ""
    return "", buffer


async def stream_chat(session: Session, user_text: str) -> AsyncIterator[dict[str, Any]]:
    """Async generator yielding SSE event dicts compatible with EventSourceResponse."""

    # Open a dedicated DB session for this stream — the request-scoped one is gone
    # by the time the generator runs.
    async with AsyncSessionLocal() as db:
        try:
            session_id = session.id
            prev_scene = SceneId(session.current_scene_id)
            prev_affinity = session.affinity
            prev_chat_count = session.chat_count
            prev_max = session.max_affinity
            prev_min = session.min_affinity

            user_msg = await _persist_message(
                db,
                session_id=session_id,
                role=MessageRole.USER,
                content=user_text,
                scene_id=prev_scene,
            )
            await _embed_silently(
                db, message_id=user_msg.id, session_id=session_id, content=user_text
            )

            snapshot = SessionSnapshot(
                session_id=str(session_id),
                player_name=session.player_name,
                scene_id=prev_scene,
                emotion=Emotion(session.emotion),
                affinity=prev_affinity,
                chat_count=prev_chat_count,
                chat_limit=session.chat_limit,
            )

            retrieved = await vector_store.search_similar(
                db, session_id=session_id, query_text=user_text, k=4
            )

            graph = get_graph()
            graph_state = await graph.ainvoke(
                {
                    "user_message": user_text,
                    "snapshot": snapshot,
                    "retrieved_messages": retrieved,
                }
            )
            is_injection = bool(graph_state.get("is_injection", False))
            affinity_delta = int(graph_state.get("affinity_delta", 0) or 0)
            new_emotion: Emotion = graph_state.get("new_emotion", snapshot.emotion)
            if not isinstance(new_emotion, Emotion):
                try:
                    new_emotion = Emotion(str(new_emotion))
                except Exception:
                    new_emotion = snapshot.emotion

            new_affinity = max(-100, min(100, prev_affinity + affinity_delta))
            new_chat_count = prev_chat_count + 1

            # 1) meta — emitted before any text so FE can prep visuals.
            yield to_event(
                "meta",
                SseMetaPayload(scene_id=prev_scene, emotion=new_emotion),
            )

            # 2) delta×N — streamed reply.
            messages = build_response_messages(
                snapshot=snapshot,
                retrieved_messages=retrieved,
                user_message=user_text,
                new_emotion=new_emotion,
                is_injection=is_injection,
            )
            full_response_parts: list[str] = []
            buffer = ""
            try:
                async for token in chat_stream(messages, temperature=0.7, max_tokens=512):
                    full_response_parts.append(token)
                    buffer += token
                    flush, buffer = _semantic_chunks(buffer)
                    if flush:
                        yield to_event("delta", SseDeltaPayload(text=flush))
                if buffer:
                    yield to_event("delta", SseDeltaPayload(text=buffer))
            except Exception as exc:  # noqa: BLE001
                log.exception("LLM streaming failed")
                yield to_event(
                    "error",
                    SseErrorPayload(code="LLM_ERROR", message=str(exc)),
                )
                return

            assistant_text = "".join(full_response_parts).strip()

            # 3) Evaluate triggers via rule engine.
            from sqlalchemy import select

            fired_stmt = select(TriggeredEvent.event_id).where(
                TriggeredEvent.session_id == session_id
            )
            fired_events: set[str] = set(
                (await db.execute(fired_stmt)).scalars().all()
            )

            triggers = evaluate_triggers(
                prev_scene=prev_scene,
                prev_affinity=prev_affinity,
                new_affinity=new_affinity,
                new_chat_count=new_chat_count,
                chat_limit=session.chat_limit,
                fired_events=fired_events,
            )

            # 4) Persist ASSISTANT message
            assistant_msg = await _persist_message(
                db,
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=assistant_text,
                emotion=new_emotion,
                scene_id=prev_scene,
                affinity_after=new_affinity,
            )
            await _embed_silently(
                db,
                message_id=assistant_msg.id,
                session_id=session_id,
                content=assistant_text,
            )

            # 5) Commit session state (affinity, chat_count, scene, emotion, ending flag).
            session_db = await db.get(Session, session_id)
            assert session_db is not None
            session_db.affinity = new_affinity
            session_db.chat_count = new_chat_count
            session_db.emotion = new_emotion.value
            session_db.max_affinity = max(prev_max, new_affinity)
            session_db.min_affinity = min(prev_min, new_affinity)
            if triggers.next_scene_id is not None:
                session_db.current_scene_id = triggers.next_scene_id.value
            if triggers.is_ending or (
                triggers.next_scene_id is not None
                and triggers.next_scene_id in ENDING_SCENE_IDS
            ):
                session_db.is_ended = True
            if triggers.event_id is not None:
                db.add(
                    TriggeredEvent(
                        session_id=session_id, event_id=triggers.event_id.value
                    )
                )
            await db.commit()

            # 6) state event
            yield to_event(
                "state",
                SseStatePayload(
                    affinity=new_affinity,
                    affinity_delta=affinity_delta,
                    progress=progress_percent(new_chat_count, session.chat_limit),
                    chat_count=new_chat_count,
                    emotion=new_emotion,
                ),
            )

            # 7) event_trigger (if any) — emitted before scene_transition (§1.6.4)
            if triggers.event_id is not None:
                yield to_event(
                    "event_trigger",
                    SseEventTriggerPayload(event_id=triggers.event_id, blocking=True),
                )

            # 8) scene_transition (if any) — INTRO→FIRST_MEET is handled by the frontend
            if triggers.next_scene_id is not None and not (
                prev_scene == SceneId.SCENE_INTRO
                and triggers.next_scene_id == SceneId.SCENE_FIRST_MEET
            ):
                yield to_event(
                    "scene_transition",
                    SseSceneTransitionPayload(next_scene_id=triggers.next_scene_id),
                )

            # 9) end
            yield to_event("end", SseEndPayload(finish_reason="complete"))

        except Exception as exc:  # noqa: BLE001
            log.exception("chat stream failed")
            yield to_event(
                "error",
                SseErrorPayload(code="LLM_ERROR", message=str(exc)),
            )
