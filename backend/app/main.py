"""FastAPI 应用入口。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import ApiError, api_error_handler
from app.api.recognitions import router as recognitions_router
from app.api.templates import router as templates_router
from app.config import settings


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    application = FastAPI(title="Form OCR API", version=__version__)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_exception_handler(ApiError, api_error_handler)
    application.include_router(templates_router)
    application.include_router(recognitions_router)

    @application.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        """返回服务健康状态。"""
        return {"status": "ok"}

    return application


app = create_app()
