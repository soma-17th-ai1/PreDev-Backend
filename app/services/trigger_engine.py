"""Pure rule engine for §1.6 — scene transition / event triggers / endings.

This module is a deterministic, side-effect-free function over the
post-chat state. The caller (chat_service) feeds in the previous scene,
the new affinity, the new chat_count, and the set of already-fired events.
"""

from dataclasses import dataclass

from app.schemas.enums import EventId, SceneId
from app.services.scene_config import SCENE_ORDER

POSITIVE_EVENT_THRESHOLDS: list[tuple[int, EventId]] = [
    (30, EventId.EVENT_LIKE_P30),
    (50, EventId.EVENT_LIKE_P50),
    (70, EventId.EVENT_LIKE_P70),
    (100, EventId.EVENT_LIKE_P100),
]

NEGATIVE_EVENT_THRESHOLDS: list[tuple[int, EventId]] = [
    (-30, EventId.EVENT_DISLIKE_M30),
    (-50, EventId.EVENT_DISLIKE_M50),
    (-70, EventId.EVENT_DISLIKE_M70),
]


@dataclass(slots=True)
class TriggerResult:
    next_scene_id: SceneId | None
    event_id: EventId | None
    is_ending: bool
    is_interrupt_bad: bool


def _ending_scene_for_affinity(affinity: int) -> SceneId:
    """§5.1 ending_id table — for normal end-of-chat-limit termination."""

    if affinity <= -30:
        return SceneId.SCENE_ENDING_BAD
    if affinity <= 0:
        return SceneId.SCENE_ENDING_NORMAL_NO_CONTACT
    if affinity <= 29:
        return SceneId.SCENE_ENDING_NORMAL_CONTACT
    if affinity <= 99:
        return SceneId.SCENE_ENDING_HAPPY
    return SceneId.SCENE_ENDING_MARRIAGE


def _check_event(
    prev_affinity: int, new_affinity: int, fired_events: set[str]
) -> EventId | None:
    """Return the event_id that fires when crossing a threshold for the first time.

    Crossing means moving from one side of the threshold to the other.
    Already-fired events never re-fire (§1.6.2).
    """

    # Positive direction (rising into +30/+50/+70/+100).
    if new_affinity > prev_affinity:
        for threshold, event in POSITIVE_EVENT_THRESHOLDS:
            if (
                prev_affinity < threshold
                and new_affinity >= threshold
                and event.value not in fired_events
            ):
                return event
    # Negative direction (falling into -30/-50/-70).
    if new_affinity < prev_affinity:
        for threshold, event in NEGATIVE_EVENT_THRESHOLDS:
            if (
                prev_affinity > threshold
                and new_affinity <= threshold
                and event.value not in fired_events
            ):
                return event
    return None


def _next_story_scene(prev_scene: SceneId, new_chat_count: int) -> SceneId | None:
    """Return the next story scene if `new_chat_count` reaches its entry threshold.

    Returns None if no transition (still in current scene).
    """

    target: SceneId | None = None
    for scene_id, threshold in SCENE_ORDER:
        if new_chat_count >= threshold:
            target = scene_id
        else:
            break
    if target is not None and target != prev_scene:
        return target
    return None


def evaluate_triggers(
    *,
    prev_scene: SceneId,
    prev_affinity: int,
    new_affinity: int,
    new_chat_count: int,
    chat_limit: int,
    fired_events: set[str],
) -> TriggerResult:
    """Apply §1.6.4 priority order:

    1. affinity ≤ -100 → instant bad ending (skip everything else).
    2. event threshold crossing → event_trigger (still allows ending/scene to follow).
    3. chat_count == chat_limit → normal ending.
    4. else: chat_count meets next scene threshold → scene_transition.
    """

    if new_affinity <= -100:
        return TriggerResult(
            next_scene_id=SceneId.SCENE_ENDING_INSTANT_BAD,
            event_id=None,
            is_ending=True,
            is_interrupt_bad=True,
        )

    event_id = _check_event(prev_affinity, new_affinity, fired_events)

    if new_chat_count >= chat_limit:
        ending_scene = _ending_scene_for_affinity(new_affinity)
        return TriggerResult(
            next_scene_id=ending_scene,
            event_id=event_id,
            is_ending=True,
            is_interrupt_bad=False,
        )

    next_scene = _next_story_scene(prev_scene, new_chat_count)
    return TriggerResult(
        next_scene_id=next_scene,
        event_id=event_id,
        is_ending=False,
        is_interrupt_bad=False,
    )
