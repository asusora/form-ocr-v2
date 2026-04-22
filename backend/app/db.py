"""数据库连接与会话管理。"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)
_engine: Engine | None = None


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类。"""


def get_engine() -> Engine:
    """按需创建并返回数据库引擎。"""
    global _engine

    if _engine is None:
        _engine = create_engine(
            settings.mysql_dsn,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            future=True,
        )
        SessionLocal.configure(bind=_engine)

    return _engine


def get_db() -> Generator[Session, None, None]:
    """提供请求级数据库会话。"""
    if SessionLocal.kw.get("bind") is None:
        get_engine()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
