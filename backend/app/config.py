"""应用配置定义。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """集中管理后端运行配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    mysql_host: str = Field(default="localhost", validation_alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, validation_alias="MYSQL_PORT")
    mysql_user: str = Field(default="form_ocr", validation_alias="MYSQL_USER")
    mysql_password: str = Field(default="form_ocr_pw", validation_alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="form_ocr", validation_alias="MYSQL_DATABASE")

    data_dir: Path = Field(default=Path("./data"), validation_alias="DATA_DIR")

    ocr_engine: str = Field(default="paddle", validation_alias="OCR_ENGINE")
    ocr_lang: str = Field(default="ch", validation_alias="OCR_LANG")
    paddle_use_gpu: bool = Field(default=False, validation_alias="PADDLE_USE_GPU")

    recognition_timeout_seconds: int = Field(
        default=90,
        validation_alias="RECOGNITION_TIMEOUT_SECONDS",
    )
    render_dpi_default: int = Field(default=200, validation_alias="RENDER_DPI_DEFAULT")
    max_pdf_mb: int = Field(default=20, validation_alias="MAX_PDF_MB")
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://localhost:5174",
        validation_alias="CORS_ORIGINS",
    )

    def model_post_init(self, __context: object) -> None:
        """在配置初始化后创建必需目录。"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def mysql_dsn(self) -> str:
        """返回 SQLAlchemy 使用的 MySQL DSN。"""
        return URL.create(
            drivername="mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)

    @property
    def cors_origins(self) -> list[str]:
        """解析允许访问的前端来源列表。"""
        raw_value = self.cors_origins_raw.strip()
        if not raw_value:
            return []
        if raw_value.startswith("["):
            parsed_value = json.loads(raw_value)
            return [str(item).strip() for item in parsed_value if str(item).strip()]
        return [item.strip() for item in raw_value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回缓存后的应用配置实例。"""
    return Settings()


settings = get_settings()
