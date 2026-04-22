"""API 路由导出。"""

from app.api.recognitions import router as recognitions_router
from app.api.templates import router as templates_router

__all__ = ["recognitions_router", "templates_router"]
