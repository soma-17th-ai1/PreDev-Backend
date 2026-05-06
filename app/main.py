import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1
from app.config import get_settings
from app.schemas.common import ApiException, err_payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lazy DB and LLM clients are created on first request.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="Soma Visual Novel Backend",
        version="1.3.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1)

    @app.exception_handler(ApiException)
    async def _api_exc(_: Request, exc: ApiException):
        return JSONResponse(
            status_code=exc.status, content=err_payload(exc.code, exc.message)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_: Request, exc: StarletteHTTPException):
        code_map = {
            400: "INVALID_INPUT",
            401: "SESSION_REQUIRED",
            404: "NOT_FOUND",
            409: "CONFLICT",
            425: "GAME_NOT_ENDED",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "ERROR")
        message = (
            exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        )
        return JSONResponse(
            status_code=exc.status_code, content=err_payload(code, message)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content=err_payload("INVALID_INPUT", str(exc.errors()[0]["msg"]) if exc.errors() else "invalid input"),
        )

    return app


app = create_app()
