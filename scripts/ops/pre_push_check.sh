#!/bin/bash
# 推送前最终检查 — 确保代码、文档、配置都到位
# 用法：bash scripts/ops/pre_push_check.sh
# 失败 exit 1，成功 exit 0

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check() {
    local name="$1"
    local path="$2"
    local is_critical="${3:-true}"

    if [ -e "$path" ]; then
        echo -e "  ${GREEN}✓${NC} $name ($path)"
        PASS=$((PASS + 1))
    else
        if [ "$is_critical" = "true" ]; then
            echo -e "  ${RED}✗${NC} $name ($path) — 缺失！"
            FAIL=$((FAIL + 1))
        else
            echo -e "  ${YELLOW}⚠${NC} $name ($path) — 缺失（建议补）"
            WARN=$((WARN + 1))
        fi
    fi
}

check_grep() {
    local name="$1"
    local file="$2"
    local pattern="$3"

    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗${NC} $name — 找不到 $pattern"
        FAIL=$((FAIL + 1))
    fi
}

cd "$(dirname "$0")/../.."

echo "═══════════════════════════════════════════════════════"
echo "  推送前检查 - $(date -Iseconds)"
echo "═══════════════════════════════════════════════════════"

# 1. 必备 GitHub 文件
echo
echo "── 1. 必备 GitHub 文件 ──"
check "README" "README.md"
check "LICENSE" "LICENSE"
check ".gitignore" ".gitignore"
check ".env.example" ".env.example"
check "requirements.txt" "requirements.txt"
check "CONTRIBUTING" "CONTRIBUTING.md"
check "SECURITY" "SECURITY.md"
check "CODE_OF_CONDUCT" "CODE_OF_CONDUCT.md"
check "Makefile" "Makefile"
check "Dockerfile (backend)" "Dockerfile"
check "Dockerfile (frontend)" "frontend/Dockerfile"
check "docker-compose" "docker-compose.yml"

# 2. GitHub 配置
echo
echo "── 2. GitHub 配置 ──"
check "Issue 模板 (bug)" ".github/ISSUE_TEMPLATE/bug_report.md"
check "Issue 模板 (feature)" ".github/ISSUE_TEMPLATE/feature_request.md"
check "PR 模板" ".github/PULL_REQUEST_TEMPLATE.md"
check "CODEOWNERS" ".github/CODEOWNERS"
check "CI workflow" ".github/workflows/ci.yml"
check "Dependabot" ".github/dependabot.yml"
check "CHANGELOG" ".github/CHANGELOG.md"

# 3. 代码完整性
echo
echo "── 3. 代码完整性 ──"
check "后端入口" "backend/main.py"
check "前端入口" "frontend/app/page.tsx"
check "前端 package.json" "frontend/package.json"
check "前端 package-lock.json" "frontend/package-lock.json"
check "前端 Dockerfile" "frontend/Dockerfile"

# 4. 文档完整性
echo
echo "── 4. 文档完整性 ──"
check "AGENTS" "AGENTS.md"
check "开发文档" "docs/初中英语AI学习Agent开发文档.md"
check "测试计划" "docs/TEST_PLAN.md"
check "运维计划" "docs/OPS_PLAN.md"
check "PM 计划" "docs/PM_PLAN.md"
check "FAQ" "docs/FAQ.md"
check "RAG 本地化" "docs/RAG_LOCALIZATION.md"
check "交叉验证" "docs/CROSS_DOC_AUDIT.md"
check "HTML 原型 README" "docs/prototypes/README.md"

# 5. .env.example 完整性
echo
echo "── 5. .env.example 关键变量 ──"
for key in MINIMAX_API_KEY PINECONE_API_KEY PINECONE_HOST JWT_SECRET DATABASE_URL EMBEDDING_MODEL VECTOR_STORE_TYPE; do
    if grep -q "^$key" .env.example; then
        echo -e "  ${GREEN}✓${NC} $key"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗${NC} $key — 缺失！"
        FAIL=$((FAIL + 1))
    fi
done

# 6. README 链接有效
echo
echo "── 6. README 关键链接 ──"
check_grep "README 提到 LICENSE" "README.md" "LICENSE"
check_grep "README 提到测试" "README.md" "TEST_PLAN"
check_grep "README 提到运维" "README.md" "OPS_PLAN"

# 7. 没有 secrets 提交
echo
echo "── 7. 防止 secrets 泄露 ──"
if grep -rE "sk-ant-[a-zA-Z0-9]{20,}" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" --include="*.yml" --include="*.json" . 2>/dev/null | grep -v "v_/site-packages/" | grep -v ".venv/" | grep -v "node_modules/" | grep -v "sk-ant-xxxx"; then
    echo -e "  ${RED}✗${NC} 可能的 Anthropic API key 泄露！"
    FAIL=$((FAIL + 1))
else
    echo -e "  ${GREEN}✓${NC} 无 Anthropic API key 模式"
    PASS=$((PASS + 1))
fi

if grep -rE "sk-cp-[a-zA-Z0-9]{20,}" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" --include="*.yml" --include="*.json" . 2>/dev/null | grep -v "v_/site-packages/" | grep -v ".venv/" | grep -v "node_modules/" | grep -v "sk-cp-xxxx"; then
    echo -e "  ${RED}✗${NC} 可能的 MiniMax API key 泄露！"
    FAIL=$((FAIL + 1))
else
    echo -e "  ${GREEN}✓${NC} 无 MiniMax API key 模式"
    PASS=$((PASS + 1))
fi

# 8. .gitignore 关键项
echo
echo "── 8. .gitignore 关键规则 ──"
for pattern in ".venv" "node_modules" ".next" "*.db" ".env" "__pycache__" ".pytest_cache"; do
    if grep -q "^$pattern" .gitignore 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $pattern"
        PASS=$((PASS + 1))
    else
        echo -e "  ${YELLOW}⚠${NC} $pattern — 未在 .gitignore"
        WARN=$((WARN + 1))
    fi
done

# 9. 大文件检查（不应提交 PDF/DB）
echo
echo "── 9. 大文件检查 ──"
LARGE_FILES=$(find . -size +1M -not -path "./.venv/*" -not -path "./node_modules/*" -not -path "./frontend/node_modules/*" -not -path "./.git/*" -not -path "./frontend/.next/*" 2>/dev/null | head -20)
if [ -n "$LARGE_FILES" ]; then
    echo -e "  ${YELLOW}⚠${NC} 发现 > 1MB 文件："
    echo "$LARGE_FILES" | sed 's/^/    /'
    WARN=$((WARN + 1))
else
    echo -e "  ${GREEN}✓${NC} 无大文件"
    PASS=$((PASS + 1))
fi

# 总结
echo
echo "═══════════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ Pass: $PASS${NC}  ${RED}✗ Fail: $FAIL${NC}  ${YELLOW}⚠ Warn: $WARN${NC}"
echo "═══════════════════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}❌ 推送前检查失败！请修复后重试。${NC}"
    exit 1
else
    echo -e "  ${GREEN}✅ 推送前检查通过！可以推送到 GitHub 了。${NC}"
    exit 0
fi
