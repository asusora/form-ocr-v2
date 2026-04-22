"""API 依赖定义。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db

DbDep = Annotated[Session, Depends(get_db)]

__all__ = ["DbDep"]
