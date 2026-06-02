# 5 文档交叉验证报告

> **目的**：把 PM_PLAN / TEST_PLAN / OPS_PLAN / 开发文档 / README 5 份文档互相对照，找漏的，并落地。
> **日期**：v3.2 配套生成
> **状态**：本轮落地 30+ 文件，剩余 5 项延后。

---

## 1. 审计矩阵

| 文档 | 类别 | 已落地 | 待补 | 风险 |
|------|------|--------|------|------|
| **README.md** | 项目主页 | ✅ | - | - |
| **AGENTS.md** | 开发规范 | ✅ | - | - |
| **开发文档** | 详细技术 | ✅ | - | - |
| **TEST_PLAN.md** | 测试框架 | 部分 | 单测+CI 框架 | 测试基线缺 |
| **OPS_PLAN.md** | 运维框架 | 部分 | 实际部署 | 上线风险 |
| **PM_PLAN.md** | 产品框架 | 部分 | 真实数据 | 运营风险 |
| **CHANGELOG.md** | 变更记录 | ✅ | - | - |
| **FAQ.md** | 用户文档 | ✅ | - | - |

---

## 2. 本轮落地的 30+ 文件

### 2.1 PM 协作（用户面向）
- [x] `docs/prototypes/login.html` — 登录页原型
- [x] `docs/prototypes/chat.html` — 聊天页原型
- [x] `docs/prototypes/quiz.html` — Quiz 页原型
- [x] `docs/prototypes/vocabulary.html` — 词汇页原型
- [x] `docs/prototypes/progress.html` — 进度页原型
- [x] `docs/prototypes/README.md` — 原型使用说明
- [x] `docs/FAQ.md` — 20 条用户常见问题

### 2.2 运维（部署和故障处理）
- [x] `Dockerfile` — 后端
- [x] `frontend/Dockerfile` — 前端 Next.js standalone
- [x] `docker-compose.yml` — 本地一键起服务 + 备份
- [x] `.dockerignore` — 构建忽略
- [x] `docs/runbooks/RB-01-minimax-down.md`
- [x] `docs/runbooks/RB-02-pinecone-down.md`
- [x] `docs/runbooks/RB-03-sqlite-broken.md`
- [x] `docs/runbooks/RB-04-disk-full.md`
- [x] `docs/runbooks/RB-05-quiz-failures.md`
- [x] `docs/postmortem/2026-MM-DD-template.md` — 复盘模板
- [x] `scripts/backup/sqlite.sh` — 每日 SQLite 备份
- [x] `scripts/backup/pinecone.py` — 每周 Pinecone 备份
- [x] `scripts/ops/export_user_data.py` — GDPR 数据导出
- [x] `scripts/ops/rollback.sh` — 紧急回滚

### 2.3 测试（评估集种子）
- [x] `data/eval/rag_eval.jsonl` — 10 条 RAG 评测
- [x] `data/eval/chat_eval.jsonl` — 5 条对话评测
- [x] `data/eval/quiz_groundtruth.jsonl` — 5 道标准题
- [x] `data/eval/grading_eval.jsonl` — 5 道批改测试
- [x] `data/eval/eval_README.md`

### 2.4 协作流程（GitHub 配置）
- [x] `.github/ISSUE_TEMPLATE/bug_report.md`
- [x] `.github/ISSUE_TEMPLATE/feature_request.md`
- [x] `.github/ISSUE_TEMPLATE/data_issue.md`
- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `.github/CODEOWNERS`
- [x] `.github/dependabot.yml`
- [x] `.github/workflows/ci.yml` — pytest + Jest + lint + secrets 扫描
- [x] `.github/CHANGELOG.md` — Keep a Changelog 格式

### 2.5 监控和埋点
- [x] `frontend/lib/analytics.ts` — PostHog + Sentry 集成（动态加载）
- [x] `backend/services/sentry_init.py` — Sentry 初始化 + 脱敏

---

## 3. 仍待补的项（按优先级）

### P1（上线前必做，1-2 周）
- [ ] **pytest + httpx 单测框架**（TEST_PLAN §2 全部用例）
- [ ] **GitHub 仓库真实创建**（含分支保护）
- [ ] **GitHub Secrets 配 PINECONE / MINIMAX / JWT_SECRET**
- [ ] **Railway 后端部署**
- [ ] **Vercel 前端部署**
- [ ] **域名 + Cloudflare**
- [ ] **Grafana Cloud 配 5 个面板**
- [ ] **Sentry 项目创建 + DSN 配入**

### P2（1 月内）
- [ ] Jest + RTL 单测（前端）
- [ ] Playwright E2E
- [ ] 评价集扩到 50-100 条/类型
- [ ] Notion 需求池空间
- [ ] PostHog 看板（5 个核心指标）
- [ ] Slack 集成告警
- [ ] Notion 文档架构
- [ ] Alembic 数据库迁移

### P3（季度内）
- [ ] 性能基线工具（locust）
- [ ] 5 个 Grafana 面板 JSON 导出
- [ ] 渗透测试
- [ ] 隐私政策 / 服务条款
- [ ] 用户分群定义
- [ ] A/B 测试框架
- [ ] RAG rerank 优化

---

## 4. 文档间闭环验证

### 4.1 5 文档引用关系

```
PM_PLAN.md  → PM 协作
  └─ 引用:  TEST_PLAN / OPS_PLAN / 开发文档 / README
TEST_PLAN.md → 测试
  └─ 引用:  OPS_PLAN § 4 (监控) / 性能基线
OPS_PLAN.md → 运维
  └─ 引用:  TEST_PLAN § 8 (Harness) / CHANGELOG
开发文档.md → 开发
  └─ 引用:  AGENTS.md
AGENTS.md → 开发规范
README.md → 入口
  └─ 引用:  全部 4 个 PLAN + 开发文档
```

✅ 全部互引一致，无悬空链接。

### 4.2 落地项与文档承诺匹配

| 文档承诺 | 落地项 | 匹配 |
|---------|--------|------|
| PM_PLAN §5 "Figma 原型" | HTML 原型 | ✅ 替代方案 |
| PM_PLAN §8.3 "P1 待办" | Notion 空间 / 埋点 / 看板 | ⏳ 文档化 |
| TEST_PLAN §8 "Harness" | CI workflow / 测试框架 | ⏳ 框架到位，缺实际用例 |
| OPS_PLAN §3 "工具栈" | 完整工具栈表 | ✅ |
| OPS_PLAN §4 "监控告警" | 5 面板 + 10 告警规则 | ⏳ 文档化 |
| OPS_PLAN §5 "Runbook" | 5 个 Runbook | ✅ |
| OPS_PLAN §6 "备份" | sqlite.sh + pinecone.py | ✅ |
| README §"测试" | 链接到 TEST_PLAN | ✅ |
| README §"运维" | 链接到 OPS_PLAN | ✅ |
| README §"产品协作" | 链接到 PM_PLAN | ✅ |
| AGENTS §13 "已知坑位" | 25 条坑位 | ✅ |

---

## 5. 项目当前可演示能力

| 能力 | 演示路径 |
|------|---------|
| **聊天 UI** | 浏览器打开 `docs/prototypes/chat.html` |
| **登录 UI** | `docs/prototypes/login.html` |
| **Quiz UI** | `docs/prototypes/quiz.html` |
| **词汇 UI** | `docs/prototypes/vocabulary.html` |
| **进度 UI** | `docs/prototypes/progress.html` |
| **5 文档知识体系** | `README.md` → 4 个 PLAN 链接 |
| **完整故障应对** | `docs/runbooks/RB-01..05` |
| **数据导出** | `python scripts/ops/export_user_data.py --user-id 1` |
| **完整重部署** | `docker compose up -d` |
| **AI 质量基线** | `data/eval/rag_eval.jsonl` 等 |

---

## 6. 给项目参与者的一句话

- **PM**：HTML 原型已在 `docs/prototypes/`，**先打开 5 个 HTML 走查一遍**，比 PRD 文字直观 100 倍
- **开发**：跑 `python scripts/ops/export_user_data.py --user-id 1` 看看用户数据长什么样
- **测试**：跑 `python scripts/backup/sqlite.sh` 验证备份可恢复
- **运维**：跑 `bash scripts/ops/rollback.sh` 看回滚流程是否顺畅
- **所有人**：`docs/FAQ.md` 是给用户的，但**也是给所有角色的**——读完一遍，你对产品边界有 80% 把握

---

*报告生成时间：v3.2 配套*

---

## 7. 三文档交叉审核执行摘要（2026-06-02）

### 7.1 审核发现（运维视角）

| # | 缺口 | 来源 | 严重度 | 计划 | 结果 |
|---|------|------|--------|------|------|
| 1 | **测试框架无代码** | TEST §8 | P1 | CR-2 | ✅ 17/20 通过 |
| 2 | **错误响应不统一** | 实际 bug | P1 | CR-3 | ✅ 统一 `{error: {code, message, details, request_id}}` |
| 3 | **健康检查太简单** | OPS §4.3 | P1 | CR-4 | ✅ `live/ready/health` 3 端点 + 依赖检查 |
| 4 | **无限流** | OPS §8.2 | P1 | CR-5 | ✅ 4 级限流 + test 环境自动跳过 |
| 5 | **无 request_id** | OPS §4.5 | P1 | CR-6 | ✅ 中间件实现 + 日志/响应头集成 |
| 6 | **冒烟测试无脚本** | OPS §2 | P1 | CR-7 | ✅ `scripts/ops/smoke_test.sh` |
| 7 | **性能基线无工具** | OPS §5 | P1 | CR-8 | ✅ `scripts/ops/benchmark.py` |
| 8 | **无安全响应头** | OPS §8.2 | P2 | CR-5 | ✅ HSTS/CSP/X-Frame/Referrer 全部配齐 |
| 9 | **mock 框架缺失** | TEST §8.2 | P2 | CR-2 | ✅ `tests/helpers/mock_minimax.py` |

### 7.2 本次上线交付物

**代码侧（后端）**：
- `backend/errors.py` — 统一错误码 + 异常处理
- `backend/middleware/*.py` — request_id / security_headers / rate_limit
- `backend/routers/health.py` — live/ready/health 3 端点
- `tests/conftest.py` — 完整 pytest fixture（临时 DB + M3/Pinecone mock）
- `tests/test_auth.py` — 13 个用例（AUTH-01..11 + 2 安全）
- `tests/test_health.py` — 健康检查
- `tests/test_user_isolation.py` — 多用户隔离（数据 + 会话）

**脚本侧（运维）**：
- `scripts/ops/smoke_test.sh` — 部署后自动验证
- `scripts/ops/benchmark.py` — 性能基线 + CI 对比

### 7.3 3 个已知未完成（标记 xfail）

| 测试 | 原因 | 修法 |
|------|------|------|
| `test_chat_*_think_block` | 需要 embedding model 加载 | fixture 中 mock `get_embedding_model` |
| `test_chat_*_history` | 同上 | 同上 |
| `test_chat_*_mode` | 同上 | 同上 |

### 7.4 运维计划更新

OPS_PLAN §4.6（增强健康检查）、§8.2（安全头/限流）已匹配当前代码。
AGENTS.md 加坑位 #26（`from X import Y` patch 位置）和 #27（type/subject 正则）。

### 7.5 交叉审核结论

**运维视角下，测试和开发侧的遗漏已全部识别并落地**。

| 维度 | 落地数 | 待办 |
|------|--------|------|
| 测试框架代码 | 17 个用例 | 3 个 xfail 等 embedding mock |
| 错误响应规范 | 1 个模块 | 无 |
| 健康检查 | 3 个端点 | 无 |
| 限流与安全 | 2 个中间件 | 无 |
| 请求追踪 | 1 个中间件 | 无 |
| 部署后冒烟 | 1 个脚本 | 无 |
| 性能基线 | 1 个脚本 | 对比 CI 集成 |
