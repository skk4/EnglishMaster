# 后端 Dockerfile
# 阶段 1：构建依赖
FROM python:3.11-slim AS builder

WORKDIR /app

# 系统依赖（sentence-transformers + torch CPU）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 阶段 2：运行时
FROM python:3.11-slim

WORKDIR /app

# 非 root 用户
RUN useradd --create-home --shell /bin/bash app
USER app

# 复制 Python 依赖
COPY --from=builder /root/.local /home/app/.local
ENV PATH=/home/app/.local/bin:$PATH

# 复制代码
COPY --chown=app:app backend/ /app/backend/
COPY --chown=app:app scripts/ /app/scripts/
COPY --chown=app:app data/ /app/data/

# 数据库目录
RUN mkdir -p /app/database && chown -R app:app /app/database
VOLUME /app/database

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health', timeout=3).raise_for_status()" \
    || exit 1

# 启动
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
