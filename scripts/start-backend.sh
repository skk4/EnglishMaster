#!/bin/bash
# 启动后端 + 自动更新 Prometheus 配置
# 用法: bash scripts/start-backend.sh 8001
PORT=${1:-8000}

cd "$(dirname "$0")/.." || exit 1

echo "Starting backend on port $PORT..."

# 1. 更新 Prometheus 配置
sed -i '' "s/host\.docker\.internal:[0-9]*/host.docker.internal:$PORT/" monitoring/prometheus.yml
echo "  Prometheus -> port $PORT"

# 2. 停旧进程
lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null

# 3. 启动
source .venv/bin/activate
uvicorn backend.main:app --port "$PORT" --reload &

sleep 2

# 4. 重启 Prometheus
docker compose -f monitoring/docker-compose.yml restart prometheus 2>/dev/null

echo "Done. Backend: http://localhost:$PORT"
echo "      Metrics:  http://localhost:$PORT/metrics"
echo "      Frontend: NEXT_PUBLIC_API_URL=http://localhost:$PORT npm run dev"
