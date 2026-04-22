#!/bin/sh

set -eu

: "${MYSQL_HOST:?MYSQL_HOST 未设置}"
: "${MYSQL_PORT:?MYSQL_PORT 未设置}"
: "${MYSQL_USER:?MYSQL_USER 未设置}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD 未设置}"
: "${MYSQL_DATABASE:?MYSQL_DATABASE 未设置}"

export MYSQL_WAIT_TIMEOUT_SECONDS="${MYSQL_WAIT_TIMEOUT_SECONDS:-60}"

python - <<'PY'
"""等待数据库可连接。"""

from __future__ import annotations

import os
import time

import pymysql


def main() -> None:
    """轮询 MySQL 直到连接成功或超时。"""
    host = os.environ["MYSQL_HOST"]
    port = int(os.environ["MYSQL_PORT"])
    user = os.environ["MYSQL_USER"]
    password = os.environ["MYSQL_PASSWORD"]
    database = os.environ["MYSQL_DATABASE"]
    timeout_seconds = int(os.environ["MYSQL_WAIT_TIMEOUT_SECONDS"])
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=5,
                read_timeout=5,
                write_timeout=5,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2)
            continue

        connection.close()
        print("数据库连接成功，继续启动服务。")
        return

    raise SystemExit(f"MySQL 在 {timeout_seconds} 秒内未就绪: {last_error}")


if __name__ == "__main__":
    main()
PY

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
