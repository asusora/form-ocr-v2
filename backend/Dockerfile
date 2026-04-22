FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN grep -vE '^paddlepaddle([[:space:]]|=|>|<|!|~)' /tmp/requirements.txt > /tmp/requirements-docker.txt \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install "paddlepaddle>=3.0.0" -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
    && python -m pip install -r /tmp/requirements-docker.txt

COPY . /app

RUN useradd --create-home --shell /bin/sh appuser \
    && mkdir -p /app/data \
    && chmod +x /app/docker/entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
