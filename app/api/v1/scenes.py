from fastapi import APIRouter, Depends

from app.deps import require_session
from app.models.orm import Session
from app.schemas.common import ApiException, ok_payload
from app.schemas.enums import SceneId
from app.services.scene_config import get_scene_info

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.get("/current")
async def get_current_scene(session: Session = Depends(require_session)):
    try:
        scene_id = SceneId(session.current_scene_id)
    except ValueError as exc:
        raise ApiException(
            code="SCENE_NOT_FOUND",
            message=f"unknown scene_id: {session.current_scene_id}",
            status=404,
        ) from exc
    return ok_payload(get_scene_info(scene_id).model_dump(mode="json"))
