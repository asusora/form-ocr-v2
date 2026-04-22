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
