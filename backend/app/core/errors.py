"""Единый формат ошибок `{code, message, details}` (§11)."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Бизнес-ошибка приложения с машиночитаемым кодом."""

    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def _payload(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def register_error_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_payload(exc.code, exc.message, exc.details))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found"}.get(exc.status_code, "http_error")
        return JSONResponse(status_code=exc.status_code, content=_payload(code, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # jsonable_encoder безопасно сериализует Decimal/прочие типы во входных данных
        return JSONResponse(
            status_code=422,
            content=_payload("validation_error", "Ошибка валидации данных", jsonable_encoder(exc.errors())),
        )


# --- Частые бизнес-ошибки (переиспользуемые фабрики) ---

def forbidden(message: str = "Недостаточно прав") -> AppError:
    return AppError("forbidden", message, status_code=403)


def not_found(message: str = "Не найдено") -> AppError:
    return AppError("not_found", message, status_code=404)


def conflict(code: str, message: str, details: Any = None) -> AppError:
    return AppError(code, message, status_code=409, details=details)


def bad_request(code: str, message: str, details: Any = None) -> AppError:
    return AppError(code, message, status_code=400, details=details)
