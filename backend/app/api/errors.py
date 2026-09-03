import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import APIError

logger = logging.getLogger(__name__)


def _payload(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_payload(exc.code, exc.message))


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    message = "; ".join(
        f"{'.'.join(str(part) for part in err.get('loc', ()) )}: {err.get('msg')}"
        for err in exc.errors()
    )
    return JSONResponse(status_code=422, content=_payload("INVALID_REQUEST", message or "Request validation failed."))


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return JSONResponse(status_code=exc.status_code, content=_payload(code, detail))


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error")
    return JSONResponse(
        status_code=500,
        content=_payload("INTERNAL_ERROR", "An unexpected error occurred."),
    )
