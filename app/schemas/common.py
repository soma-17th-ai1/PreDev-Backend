from typing import Any, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    ok: bool
    data: T | None = None
    error: ApiError | None = None


def ok_payload(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def err_payload(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def err_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content=err_payload(code, message))


class ApiException(Exception):
    """Application-level exception that maps to the spec's error format."""

    def __init__(self, *, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
