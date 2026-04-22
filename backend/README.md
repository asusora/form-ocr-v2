# Form OCR Backend

## 项目说明

该目录是表单 OCR 模板化识别系统的后端实现，采用 FastAPI、SQLAlchemy、Alembic 与 MySQL。

## 快速启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install "paddlepaddle>=3.0.0" -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install -e .[dev]
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

如果需要 GPU 推理，不要直接复用上面的 CPU 安装命令，应先按 PaddlePaddle 官方文档安装对应平台的 GPU 版本，再执行 `pip install -e .[dev]`。

## 测试

```bash
cd backend
pytest -v
```

## Docker 镜像构建

### 本地构建

```bash
cd backend
docker build -t form-ocr-backend:local .
```

镜像默认使用 CPU 版本 PaddlePaddle，并在容器启动时自动执行：

1. 等待 MySQL 可连接。
2. 执行 `alembic upgrade head`。
3. 启动 `uvicorn app.main:app --host 0.0.0.0 --port 8000`。

### GitHub Actions 自动构建与推送

仓库需要预先配置以下 GitHub Secrets / Variables：

```text
Secrets:
- DOCKERHUB_USERNAME
- DOCKERHUB_TOKEN

Variables:
- DOCKERHUB_REPOSITORY
```

其中 `DOCKERHUB_REPOSITORY` 的值应为完整仓库名，例如：

```text
asusora/form-ocr-backend
```

工作流文件位于：

```text
.github/workflows/backend-docker.yml
```

触发规则如下：

1. `pull_request`：只做镜像构建校验，不推送。
2. `push main`：当且仅当上述 Secrets / Variables 都已配置时，推送 `latest` 和 `sha-<7位提交号>` 两个标签。
3. `workflow_dispatch`：可手动触发构建校验；若在 `main` 分支且凭据齐全，也会推送镜像。

## Docker Compose 手动部署

### 1. 准备环境文件

```bash
cd backend
cp .env.example .env
```

至少要按服务器实际情况修改：

```text
MYSQL_ROOT_PASSWORD
MYSQL_PASSWORD
CORS_ORIGINS
BACKEND_IMAGE
BACKEND_PORT
```

其中 `BACKEND_IMAGE` 应指向 Docker Hub 中已构建好的镜像，例如：

```text
BACKEND_IMAGE=asusora/form-ocr-backend:latest
```

### 2. 启动服务

```bash
cd backend
docker compose up -d
```

### 3. 查看运行状态

```bash
docker compose ps
docker compose logs -f backend
```

后端健康检查地址：

```bash
http://127.0.0.1:8000/api/health
```
