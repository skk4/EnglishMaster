#!/bin/bash
# 紧急回滚脚本
# 用法：./scripts/ops/rollback.sh v3.2
# 或：./scripts/ops/rollback.sh  # 回滚到上一个版本

set -euo pipefail

TARGET_VERSION="${1:-}"

# 检测平台
if command -v railway &> /dev/null && [ -n "${RAILWAY_TOKEN:-}" ]; then
    PLATFORM="railway"
elif command -v vercel &> /dev/null && [ -n "${VERCEL_TOKEN:-}" ]; then
    PLATFORM="vercel"
else
    PLATFORM="manual"
fi

echo "[rollback] Platform: $PLATFORM"
echo "[rollback] Target version: ${TARGET_VERSION:-<previous>}"

# 1. 通知 Slack
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -sS -X POST "$SLACK_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"⚠️ Rolling back ${TARGET_VERSION:-to previous version} on $PLATFORM at $(date -Iseconds)\"}"
fi

# 2. 执行回滚
case $PLATFORM in
    railway)
        if [ -n "$TARGET_VERSION" ]; then
            railway rollback --to "$TARGET_VERSION"
        else
            railway rollback
        fi
        ;;
    vercel)
        if [ -n "$TARGET_VERSION" ]; then
            vercel rollback "$TARGET_VERSION"
        else
            vercel rollback
        fi
        ;;
    manual)
        echo "[rollback] Manual mode. 请按平台文档操作："
        echo "  Railway:  https://railway.app/project/{id}/deployments → Previous → Redeploy"
        echo "  Vercel:   https://vercel.com/{team}/project/deployments → Promote previous"
        echo "  自建:     ssh user@server && cd /app && git checkout <version> && docker compose up -d"
        ;;
esac

# 3. 等待 30s
echo "[rollback] Waiting 30s for service to stabilize..."
sleep 30

# 4. 健康检查
echo "[rollback] Health check:"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
if curl -fsS "$BACKEND_URL/api/health" > /dev/null; then
    echo "  ✅ Backend OK"
else
    echo "  ❌ Backend FAILED - investigate immediately"
    exit 1
fi

# 5. 通知
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -sS -X POST "$SLACK_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"✅ Rollback to ${TARGET_VERSION:-previous} complete. Backend healthy. Postmortem pending.\"}"
fi

echo "[rollback] Done at $(date -Iseconds)"
echo "[rollback] Remember: write postmortem within 24h!"
