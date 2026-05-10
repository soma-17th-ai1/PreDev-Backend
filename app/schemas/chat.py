from pydantic import BaseModel, Field

from app.schemas.enums import Emotion, EventId, SceneId


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=300)


class SseMetaPayload(BaseModel):
    scene_id: SceneId
    emotion: Emotion


class SseDeltaPayload(BaseModel):
    text: str


class SseStatePayload(BaseModel):
    affinity: int
    affinity_delta: int
    progress: int
    chat_count: int
    emotion: Emotion


class SseEventTriggerPayload(BaseModel):
    event_id: EventId
    blocking: bool = True


class SseSceneTransitionPayload(BaseModel):
    next_scene_id: SceneId


class SseEndPayload(BaseModel):
    finish_reason: str = "complete"


class SseErrorPayload(BaseModel):
    code: str
    message: str


class SessionCreateRequest(BaseModel):
    force_reset: bool = False


class SessionStartRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=20)


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


class HistoryQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    before: str | None = None
