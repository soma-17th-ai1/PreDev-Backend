from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_session
from app.models.orm import Session
from app.schemas.common import ok_payload
from app.schemas.enums import SceneId

router = APIRouter(prefix="/dev", tags=["dev"])


class ForceEndingRequest(BaseModel):
    affinity: int = Field(..., ge=-100, le=100)


def _ending_scene(affinity: int) -> SceneId:
    if affinity <= -100:
        return SceneId.SCENE_ENDING_INSTANT_BAD
    if affinity <= -30:
        return SceneId.SCENE_ENDING_BAD
    if affinity <= 0:
        return SceneId.SCENE_ENDING_NORMAL_NO_CONTACT
    if affinity <= 29:
        return SceneId.SCENE_ENDING_NORMAL_CONTACT
    if affinity <= 99:
        return SceneId.SCENE_ENDING_HAPPY
    return SceneId.SCENE_ENDING_MARRIAGE


@router.post("/force-ending")
async def force_ending(
    body: ForceEndingRequest,
    db: AsyncSession = Depends(get_db),
    session: Session = Depends(require_session),
):
    scene = _ending_scene(body.affinity)
    session.affinity = body.affinity
    session.current_scene_id = scene.value
    session.is_ended = True
    session.is_started = True
    await db.commit()
    return ok_payload({"affinity": body.affinity, "ending_scene": scene.value})
