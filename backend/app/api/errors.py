"""API 错误处理。"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """统一 API 业务错误。"""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    """把业务异常转换成统一 JSON 响应。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


def not_found(message: str, code: str = "NOT_FOUND") -> ApiError:
    """构造 404 业务异常。"""
    return ApiError(status_code=404, detail=message, code=code)


def bad_request(message: str, code: str = "BAD_REQUEST") -> ApiError:
    """构造 400 业务异常。"""
    return ApiError(status_code=400, detail=message, code=code)


def service_unavailable(message: str, code: str = "SERVICE_UNAVAILABLE") -> ApiError:
    """构造 503 业务异常。"""
    return ApiError(status_code=503, detail=message, code=code)
