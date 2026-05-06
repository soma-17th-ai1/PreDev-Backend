from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.enums import Emotion, EndingId, EventId, MessageRole, SceneId


class GameState(BaseModel):
    player_name: str | None = None
    affinity: int = 0
    chat_count: int = 0
    chat_limit: int = 50
    progress: int = 0
    current_scene_id: SceneId
    emotion: Emotion = Emotion.NEUTRAL
    is_ended: bool = False


class IntroDialogueNarration(BaseModel):
    type: Literal["narration"] = "narration"
    text: str


class IntroDialogueCharacter(BaseModel):
    type: Literal["character"] = "character"
    name: str
    emotion: Emotion
    text: str


IntroDialogue = IntroDialogueNarration | IntroDialogueCharacter


class SceneInfo(BaseModel):
    scene_id: SceneId
    title: str
    intro_dialogues: list[IntroDialogue] = Field(default_factory=list)


class RecentMessage(BaseModel):
    role: MessageRole
    content: str
    emotion: Emotion | None = None
    timestamp: datetime


class HistoryMessage(BaseModel):
    message_id: str
    role: MessageRole
    content: str
    emotion: Emotion | None = None
    scene_id: SceneId | None = None
    timestamp: datetime


class EndingStats(BaseModel):
    total_chats: int
    max_affinity: int
    min_affinity: int
    events_triggered: list[EventId]


class EndingPayload(BaseModel):
    ending_id: EndingId
    title: str
    narrative: str
    final_affinity: int
    stats: EndingStats


class SessionStateSnapshot(BaseModel):
    """Lightweight session info for §2.1."""

    has_session: bool
    is_started: bool = False
    current_scene_id: SceneId | None = None
    progress: int | None = None
    is_ended: bool | None = None
