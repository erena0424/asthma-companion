"""Shared API error types."""

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, detail: str, code: str):
        self.status_code = status_code
        self.detail = detail
        self.code = code


def api_error(status_code: int, detail: str, code: str) -> APIError:
    return APIError(status_code=status_code, detail=detail, code=code)


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )
