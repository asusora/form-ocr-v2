# Backend DockerHub Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为后端补齐可构建的 Docker 镜像、手动 `docker compose` 部署入口，以及 GitHub Actions 自动构建并在配置凭据后推送到 Docker Hub 的流水线。

**Architecture:** 以后端目录为单一构建上下文，使用 `python:3.11-slim` 构建 CPU 版本镜像。容器启动时先等待 MySQL 可连接并执行 Alembic 迁移，再启动 FastAPI；GitHub Actions 负责构建校验与镜像推送，部署仍由人工在服务器执行 `docker compose up -d`。

**Tech Stack:** Docker、Docker Compose、GitHub Actions、Python 3.11、FastAPI、Alembic、MySQL

---

### Task 1: 规划后端容器文件边界

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/docker/entrypoint.sh`
- Modify: `backend/docker-compose.yml`
- Modify: `backend/README.md`
- Create: `.github/workflows/backend-docker.yml`

- [ ] **Step 1: 确认镜像责任边界**

约束：

```text
backend/Dockerfile         只负责镜像构建
backend/docker/entrypoint.sh 只负责等待数据库、迁移、启动服务
backend/docker-compose.yml 只负责本机/服务器的编排
.github/workflows/backend-docker.yml 只负责 CI 构建与推送
backend/README.md          只负责部署说明与凭据说明
```

- [ ] **Step 2: 确认部署策略**

策略：

```text
镜像仓库：Docker Hub
推送触发：push 到 main
构建校验：pull_request、push、workflow_dispatch
部署方式：人工在 backend 目录执行 docker compose up -d
镜像标签：latest + sha-<7位提交号>
平台：linux/amd64
```

- [ ] **Step 3: 提交本阶段变更**

Run:

```bash
git add docs/superpowers/plans/2026-04-22-backend-dockerhub-delivery.md
git commit -m "docs: add backend docker delivery plan"
```

Expected: 计划文档成功入库。

### Task 2: 补齐后端镜像与启动脚本

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/docker/entrypoint.sh`

- [ ] **Step 1: 写镜像构建文件**

目标代码：

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
```

- [ ] **Step 2: 添加运行依赖与 Python 依赖安装逻辑**

要求：

```text
安装 curl、build-essential、libglib2.0-0、libgomp1、libsm6、libxext6、libxrender1
先单独安装 paddlepaddle CPU 包，再安装剔除 paddlepaddle 行后的 requirements.txt
复制 backend 源码到 /app
```

- [ ] **Step 3: 写容器启动脚本**

目标逻辑：

```bash
1. 检查 MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE
2. 用 Python + PyMySQL 轮询数据库连接，最多等待 60 秒
3. 执行 alembic upgrade head
4. exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 4: 写镜像忽略规则**

要求：

```text
忽略 .env、.venv、tests、data、__pycache__、*.pyc、form_ocr_backend.egg-info
```

- [ ] **Step 5: 本地构建验证**

Run:

```bash
docker build -f backend/Dockerfile -t form-ocr-backend:test backend
```

Expected: 镜像成功构建，退出码为 0。

### Task 3: 扩展手动部署 compose

**Files:**
- Modify: `backend/docker-compose.yml`

- [ ] **Step 1: 给 MySQL 加健康检查**

目标代码：

```yaml
healthcheck:
  test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -uroot -p$$MYSQL_ROOT_PASSWORD --silent"]
  interval: 10s
  timeout: 5s
  retries: 12
  start_period: 20s
```

- [ ] **Step 2: 新增 backend 服务**

目标逻辑：

```yaml
backend:
  image: ${BACKEND_IMAGE:-your-dockerhub-username/form-ocr-backend:latest}
  depends_on:
    mysql:
      condition: service_healthy
  env_file:
    - .env
  environment:
    MYSQL_HOST: mysql
    MYSQL_PORT: 3306
    DATA_DIR: /app/data
  ports:
    - "${BACKEND_PORT:-8000}:8000"
  volumes:
    - backend_data:/app/data
  restart: unless-stopped
```

- [ ] **Step 3: 验证编排文件**

Run:

```bash
docker compose -f backend/docker-compose.yml config
```

Expected: YAML 展开成功，没有语法错误。

### Task 4: 新增 GitHub Actions 自动构建与推送

**Files:**
- Create: `.github/workflows/backend-docker.yml`

- [ ] **Step 1: 定义触发器与并发取消**

目标代码：

```yaml
on:
  push:
    branches: ["main"]
  pull_request:
    paths:
      - "backend/**"
      - ".github/workflows/backend-docker.yml"
  workflow_dispatch:
```

- [ ] **Step 2: 定义 build 作业**

要求：

```text
使用 docker/setup-buildx-action
构建上下文为 backend
文件为 backend/Dockerfile
pull_request 和未配置凭据时只 build 不 push
```

- [ ] **Step 3: 定义 push 条件**

要求：

```text
只有 push 到 main 且 DOCKERHUB_USERNAME、DOCKERHUB_TOKEN、DOCKERHUB_REPOSITORY 都非空时才登录并推送
标签输出 latest 与 sha-<7位提交号>
```

- [ ] **Step 4: 校验工作流**

Run:

```bash
python - <<'PY'
from pathlib import Path
import yaml
workflow = yaml.safe_load(Path(".github/workflows/backend-docker.yml").read_text(encoding="utf-8"))
assert "jobs" in workflow
assert "backend-docker" in workflow["name"].lower()
PY
```

Expected: 脚本退出码为 0。

### Task 5: 更新部署文档并做最终验证

**Files:**
- Modify: `backend/README.md`

- [ ] **Step 1: 写 Docker 部署章节**

要求：

```text
写明需要配置的 GitHub Secrets/Variables
写明服务器端如何准备 .env
写明 BACKEND_IMAGE 如何指向 Docker Hub 镜像
写明在 backend 目录执行 docker compose up -d
```

- [ ] **Step 2: 运行最终验证命令**

Run:

```bash
docker build -f backend/Dockerfile -t form-ocr-backend:test backend
docker compose -f backend/docker-compose.yml config > /tmp/form-ocr-compose.out
git diff --stat
```

Expected: Docker 构建成功，compose 配置成功展开，diff 仅包含本次目标文件。

- [ ] **Step 3: 提交实现**

Run:

```bash
git add backend/Dockerfile backend/.dockerignore backend/docker/entrypoint.sh backend/docker-compose.yml backend/README.md .github/workflows/backend-docker.yml
git commit -m "feat: add backend docker build pipeline"
```

Expected: Docker 构建链、工作流和文档一次性提交完成。
