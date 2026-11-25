import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from copilot_api.core.middleware import REQUEST_ID_HEADER
from copilot_api.schemas.errors import ErrorBody, ErrorResponse, ValidationIssue

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "rate_limit_exceeded",
    503: "service_unavailable",
}


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ValidationIssue] | None = None,
) -> JSONResponse:
    request_id = request.state.request_id
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers={REQUEST_ID_HEADER: request_id},
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(
        request,
        exc.status_code,
        _STATUS_CODES.get(exc.status_code, "http_error"),
        message,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        ValidationIssue(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
            type=error["type"],
        )
        for error in exc.errors()
    ]
    return _error_response(
        request,
        422,
        "validation_error",
        "Request validation failed.",
        details,
    )


async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.state.request_id
    logger.error(
        "Unhandled application error",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"request_id": request_id},
    )
    return _error_response(
        request,
        500,
        "internal_error",
        "Internal server error.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, internal_exception_handler)
