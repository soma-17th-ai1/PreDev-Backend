import json
from typing import Any

from pydantic import BaseModel


def to_event(event: str, payload: BaseModel | dict[str, Any]) -> dict[str, str]:
    """Build the dict shape expected by sse-starlette's EventSourceResponse."""

    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json", exclude_none=True)
    else:
        data = payload
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}
