#!/bin/bash
# 部署后冒烟测试
# 用途：Railway health check / 手动验证部署
# 用法：./scripts/ops/smoke_test.sh [BASE_URL]

set -uo pipefail

BASE_URL="${1:-${SMOKE_URL:-http://localhost:8000}}"
TIMEOUT="${SMOKE_TIMEOUT:-10}"

PASS=0
FAIL=0

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check() {
    local name="$1"
    local expected_code="$2"
    local method="${3:-GET}"
    local path="$4"
    local auth="${5:-}"

    local args=(-sS -o /tmp/smoke_resp -w "%{http_code}" -X "$method" --max-time "$TIMEOUT")
    if [ -n "$auth" ]; then
        args+=(-H "Authorization: Bearer $auth")
    fi
    if [ "$method" = "POST" ]; then
        args+=(-H "Content-Type: application/json" -d '{}')
    fi

    local code
    code=$(curl "${args[@]}" "$BASE_URL$path" 2>/dev/null || echo "000")

    if [ "$code" = "$expected_code" ]; then
        echo -e "${GREEN}✓${NC} $name: $code"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} $name: expected $expected_code, got $code"
        echo "    Response body:"
        head -c 200 /tmp/smoke_resp 2>/dev/null | sed 's/^/    /'
        FAIL=$((FAIL + 1))
    fi
}

echo "═══════════════════════════════════════════════════════"
echo "Smoke Test: $BASE_URL"
echo "═══════════════════════════════════════════════════════"

# 1. 进程存活（liveness）
check "Liveness probe" 200 GET "/api/health/live"

# 2. 完整健康（readiness，含依赖）
check "Readiness probe" 200 GET "/api/health/ready"

# 3. 健康检查
check "Health check" 200 GET "/api/health"

# 4. 错误响应格式
check "401 on no token" 401 GET "/api/auth/me"

# 5. 注册 + 登录
echo
echo "── 认证流程 ──"
REGISTER_RESP=$(curl -sS -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"smoke_$(date +%s)\",\"password\":\"smoke1234\"}")
TOKEN=$(echo "$REGISTER_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓${NC} Register: got token"

    # 6. /me
    check "Get current user" 200 GET "/api/auth/me" "$TOKEN"

    # 7. 聊天（可能慢，给 15s）
    echo
    echo "── AI 接口（可能 5-15s）──"
    SMOKE_TIMEOUT=15 check "Chat sync (mock slow)" 200 POST "/api/chat/sync" "$TOKEN"

    # 8. 出题（最可能失败）
    SMOKE_TIMEOUT=30 check "Quiz generate" 200 POST "/api/quiz/generate" "$TOKEN"

    # 9. 词汇练习
    check "Vocab practice" 200 GET "/api/vocab/practice?semester=1&n=5" "$TOKEN"

    # 10. 进度
    check "Progress summary" 200 GET "/api/progress/summary" "$TOKEN"

    # 11. 对话历史
    check "Chat sessions list" 200 GET "/api/history/sessions" "$TOKEN"

    # 12. 验证 X-Request-ID 响应头
    echo
    echo "── 安全检查 ──"
    RESP=$(curl -sS -D - -o /dev/null "$BASE_URL/api/health")
    if echo "$RESP" | grep -qi "X-Request-ID"; then
        echo -e "${GREEN}✓${NC} X-Request-ID 响应头存在"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} X-Request-ID 响应头缺失"
        FAIL=$((FAIL + 1))
    fi

    if echo "$RESP" | grep -qi "X-Content-Type-Options: nosniff"; then
        echo -e "${GREEN}✓${NC} X-Content-Type-Options 头存在"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} X-Content-Type-Options 头缺失"
        FAIL=$((FAIL + 1))
    fi

    if echo "$RESP" | grep -qi "Strict-Transport-Security"; then
        echo -e "${GREEN}✓${NC} HSTS 头存在"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}✗${NC} HSTS 头缺失"
        FAIL=$((FAIL + 1))
    fi
else
    echo -e "${RED}✗${NC} Register failed: $REGISTER_RESP"
    FAIL=$((FAIL + 1))
fi

echo
echo "═══════════════════════════════════════════════════════"
echo -e "Result: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}"
echo "═══════════════════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}✗ Smoke test FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Smoke test PASSED${NC}"
    exit 0
fi
