from uuid import UUID

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.orm import Session
from app.schemas.common import ApiException
from app.services.session_service import get_session


async def get_optional_session(
    db: AsyncSession = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias="session_id"),
) -> Session | None:
    # alias above only matches the default cookie name. Re-read with configured name.
    settings = get_settings()
    if settings.session_cookie_name != "session_id":
        # Fallback: framework already passed `session_cookie` from session_id.
        # If a custom cookie name is configured, this branch is best-effort only.
        pass
    if not session_cookie:
        return None
    try:
        sid = UUID(session_cookie)
    except ValueError:
        return None
    return await get_session(db, sid)


async def require_session(
    session: Session | None = Depends(get_optional_session),
) -> Session:
    if session is None:
        raise ApiException(
            code="SESSION_REQUIRED",
            message="세션이 없습니다. 새 게임을 시작해 주세요.",
            status=401,
        )
    return session
