# EnglishMaster Agent — 运维计划

> **目标读者**：运维工程师、SRE、技术 Lead
> **状态**：v1.0（待评审）
> **更新原则**：每次发布后更新基线；每次事故后更新 Runbook

---

## 目录

1. [总览与角色协作矩阵](#1-总览与角色协作矩阵)
2. [生命周期七阶段](#2-生命周期七阶段)
3. [工具栈与平台选择](#3-工具栈与平台选择)
4. [监控、日志与告警](#4-监控日志与告警)
5. [事件响应与 Runbook](#5-事件响应与-runbook)
6. [备份与灾难恢复](#6-备份与灾难恢复)
7. [成本估算](#7-成本估算)
8. [安全与合规](#8-安全与合规)
9. [变更与发布管理](#9-变更与发布管理)
10. [运维待办（Roadmap）](#10-运维待办roadmap)

---

## 1. 总览与角色协作矩阵

### 1.1 现状盘点（v3.2）

| 资产 | 状态 | 位置 |
|------|------|------|
| 后端代码 | ✅ 本地可跑（`uvicorn backend.main:app`） | `backend/` |
| 前端代码 | ✅ 本地可跑（`npm run dev`） | `frontend/` |
| Pinecone Index | ✅ 841 vectors 1024维 | `xsjkndb01` AWS us-east-1 |
| MiniMax Token Plan | ✅ sk-cp-xxx 配额 ~0.5B/月 | MiniMax 平台 |
| SQLite | ✅ 用户/进度/对话/词汇 | `database/app.db` 本地 |
| 测试框架 | ❌ 无（v3.2 待建） | `tests/` 待建 |
| CI/CD | ❌ 无（手动部署） | `.github/workflows/` 待建 |
| 生产环境 | ❌ 无（仅本地） | 待部署 |
| 监控 | ❌ 无 | 待建 |
| 备份 | ❌ 无 | 待建 |

### 1.2 运维目标

| 目标 | 衡量 |
|------|------|
| **可用性** | 月度 uptime ≥ 99.5% |
| **性能** | P95 聊天 ≤ 8s、出题 ≤ 15s |
| **安全** | 无 P0/P1 安全漏洞、所有 secrets 加密 |
| **成本** | 月度运营成本 ≤ $30（学生用预算低） |
| **响应** | P0 故障 ≤ 30min 响应、≤ 4h 修复 |
| **可观测** | 100% 请求有 trace_id、日志可聚合 |
| **可回滚** | 任意发布 ≤ 5min 内可回退 |

### 1.3 四角色协作矩阵

| 阶段 | 开发 | 测试 | 产品 | **运维** |
|------|------|------|------|---------|
| 需求评审 | 提供技术评估 | 提供测试可行性 | 主持 | 评估部署/成本 |
| 开发 | 写代码 + 单测 | 准备测试用例 | 验收标准 | 配 CI 环境 |
| 提 PR | 跑单测 | 跑集成测试 | 验收 | 监控 CI |
| 合并 | - | - | - | 触发自动部署 |
| 预发 | - | 跑 smoke test | UAT | 部署 staging |
| 生产发布 | on-call 准备 | 跑回归 | 业务验证 | 执行发布 + 监控 |
| 监控期 | - | - | 收集反馈 | 看指标 + 处理告警 |
| 复盘 | 提供根因 | 提供测试 | 业务影响 | 主持、记录改进项 |

### 1.4 协作原则

- **运维是"守门人"**：决定能否上线
- **故障时谁响应谁指挥**：P0 故障由运维指挥，所有人配合
- **变更必须可回滚**：任何发布前必须确认回滚方案
- **文档即代码**：所有决策、Runbook、SOP 进 Git 仓库

### 1.5 信息共享

| 内容 | 位置 | 更新者 |
|------|------|--------|
| 架构图 | `docs/architecture/` | 架构师 |
| 服务清单 | `OPS_PLAN.md` §3 | 运维 |
| OnCall 排班 | PagerDuty / OpsGenie | 运维 Lead |
| 事故复盘 | `docs/postmortem/YYYY-MM-DD-*.md` | 故障响应者 |
| SLO 报表 | Grafana 面板 | 自动化 |

---

## 2. 生命周期七阶段

### 阶段 1：环境准备（一次性，1-2 天）

| 任务 | 工具 | 命令/动作 | 责任人 |
|------|------|----------|--------|
| GitHub 仓库创建 + 分支保护 | GitHub | `main` 保护，需 PR review | 运维 |
| 添加协作者 | GitHub | Settings → Collaborators | 运维 |
| 配 GitHub Secrets | GitHub | `PINECONE_API_KEY`、`MINIMAX_API_KEY`、`JWT_SECRET` | 运维 |
| 选 PaaS | Railway | 注册 Team 计划、绑定 GitHub | 运维 |
| 选监控 | Grafana Cloud | 注册 free tier | 运维 |
| 选错误追踪 | Sentry | 注册项目、获取 DSN | 运维 |
| 选日志 | Better Stack 或 Loki | 决定 | 运维 |
| 域名 | Namecheap / Cloudflare | 购买、解析 | 运维 |
| HTTPS | Cloudflare | 自动 + 免费 | 运维 |
| Slack/Discord | Slack | 创建 #englishmaster 频道 | 运维 |

**产出**：环境 ready 清单（`docs/ops_checklist.md`）

---

### 阶段 2：CI/CD 配置（一次性，2-3 天）

| 任务 | 工具/文件 | 关键内容 |
|------|----------|---------|
| GitHub Actions 工作流 | `.github/workflows/ci.yml` | 跑 pytest、Jest、lint |
| GitHub Actions 部署 | `.github/workflows/deploy.yml` | merge main → 自动部署 staging |
| Docker 化后端 | `backend/Dockerfile` | python:3.11-slim + uvicorn |
| Docker 化前端 | `frontend/Dockerfile` | node:20 → next build → standalone |
| Docker Compose | `docker-compose.yml` | 本地一栈起后端+前端+nginx |
| 镜像仓库 | GitHub Container Registry | ghcr.io，免费 |
| 镜像扫描 | Trivy | 每次 push 扫 CVE |
| Secret 扫描 | GitHub Secret Scanning | 默认开启 |
| Dependabot | GitHub | 自动 PR 依赖更新 |

**关键文件示例**：
- `Dockerfile`（后端）：基于 `python:3.11-slim`，装依赖，启 uvicorn
- `docker-compose.yml`：3 服务（backend/frontend/nginx），共享 network
- `.github/workflows/ci.yml`：见 TEST_PLAN §8.5.1

**产出**：
- 每次 push 自动跑测试
- 每次 merge main 自动部署 staging
- PR 必须通过 CI 才能合

---

### 阶段 3：测试协作（持续）

| 任务 | 工具 | 动作 |
|------|------|------|
| 单元测试 | pytest + Jest | 开发本地 `make test-fast` |
| 集成测试 | pytest + httpx | CI 自动跑 |
| E2E | Playwright | CI 自动跑 |
| 性能压测 | locust | 每周一次 + 发布前 |
| AI 评估 | `scripts/eval_*.py` | 每周抽检 + 改 prompt 时 |
| 兼容性测试 | BrowserStack | 每月，新浏览器版本 |
| 渗透测试 | OWASP ZAP | 每年或重大发布前 |

**协作流程**：
```
开发写完单测 → 提 PR → CI 自动跑集成 → 测试 review → merge → CI 自动跑 E2E
```

**失败响应**：
- 单测失败：开发自己修
- 集成失败：开发 + 后端共同 review
- E2E 失败：前端 + 测试 review（可能前端改动影响 flow）
- 性能退化 > 20%：阻塞发布

---

### 阶段 4：灰度发布（每次发布）

| 步骤 | 工具/动作 | 责任人 |
|------|----------|--------|
| 1. 准备发布 | 写 changelog、PR → main | 开发 |
| 2. 触发 staging | merge → Actions 自动 deploy | 自动化 |
| 3. Smoke test | `curl /api/health`、前端首页 200 | 运维 |
| 4. 灰度 10% | Railway 设环境变量 `ROLLOUT_PERCENT=10` | 运维 |
| 5. 监控 30min | 看 Grafana 错误率、延迟 | 运维 |
| 6. 全量 100% | 改 `ROLLOUT_PERCENT=100` | 运维 |
| 7. 通知 | Slack #englishmaster 发"v3.3 已发布" | 运维 |
| 8. 持续监控 24h | on-call 关注告警 | 运维 |

**回滚条件**（任一即回滚）：
- 错误率 > 5%
- P95 延迟 > 2 倍基线
- 任何 P0 报告
- 健康检查连续 3 次失败

**回滚命令**：
```bash
# Railway 一键回滚
railway rollback --to v3.2
# 或通过 UI：Deployments → Previous → Redeploy
```

---

### 阶段 5：监控告警（持续，部署后立即配）

#### 5.1 监控面板（Grafana）

5 个核心面板：
1. **业务指标**：DAU、出题数、平均对话轮数
2. **API 健康**：QPS、P50/P95/P99、错误率（按端点）
3. **AI 调用**：M3 token 消耗、retry 率、截断率
4. **资源**：CPU、内存、磁盘、网络出口
5. **依赖**：Pinecone 延迟、M3 API 错误率

#### 5.2 告警规则

| 级别 | 触发 | 通知 |
|------|------|------|
| P0 | API 完全不可用（5xx > 50% 持续 2 分钟） | 立即电话 + Slack |
| P1 | 错误率 > 5% 持续 5 分钟 | Slack @oncall |
| P1 | P95 延迟 > 2 倍基线持续 10 分钟 | Slack @oncall |
| P2 | 错误率 > 1% 持续 10 分钟 | Slack 频道 |
| P2 | M3 token 单日 > 月预算 50% | Slack 频道 |
| P3 | 磁盘 > 80% | 邮件 |

#### 5.3 健康检查

```bash
# Railway / Render / 自建都支持
curl -fsS https://api.englishmaster.com/api/health
# 期望：200 {"status":"ok","model":"MiniMax-M3"}
```

健康检查间隔：30s。失败 3 次重启容器。

---

### 阶段 6：备份恢复（持续）

| 数据 | 备份方式 | 频率 | 保留期 | RPO |
|------|---------|------|--------|-----|
| 代码 | GitHub（自带） | 每次 push | 永久 | 0 |
| SQLite | cron 复制到 S3 | 每天 03:00 | 30 天 | ≤ 1 天 |
| Pinecone vectors | 描述快照（元数据可重建） | 每周 | 永久 | 可重建（重跑 03） |
| 环境变量 | 1Password / Vault 备份 | 每次变更 | 永久 | 0 |
| 用户上传文件 | S3 跨区复制 | 实时 | 永久 | 0 |
| 文档 | GitHub 仓库 | 每次 push | 永久 | 0 |

**恢复演练**：每季度一次，模拟"DB 损坏" → 用备份恢复 → 验证服务正常。

**RTO/RPO 目标**：
- RTO（恢复时间） ≤ 4h
- RPO（数据丢失） ≤ 24h

---

### 阶段 7：下线与归档（项目结束时）

| 任务 | 工具 | 动作 |
|------|------|------|
| 通知用户 | 邮件/Slack | 提前 30 天 |
| 数据导出 | 工具脚本 | 给用户导出聊天/进度 |
| 停止服务 | Railway | 关停实例 |
| 备份归档 | S3 Glacier | 移到冷存储 |
| 删除资源 | 各平台 | 删 Pinecone Index、域名、SSL |
| 文档封存 | GitHub | 仓库 archive，加 README 说明 |

---

## 3. 工具栈与平台选择

### 3.1 一览表

| 类别 | 工具 | 替代方案 | 选择理由 |
|------|------|---------|---------|
| **代码托管** | GitHub | GitLab / Bitbucket | 团队熟悉、CI 集成好 |
| **CI/CD** | GitHub Actions | CircleCI / Jenkins | 与 GitHub 一体、免费 2000 min/月 |
| **镜像仓库** | GitHub Container Registry (ghcr.io) | Docker Hub | 免费、私有 |
| **生产环境** | Railway | Render / Fly.io / AWS ECS | 简单、自动 SSL、$5/月起 |
| **静态前端** | Vercel | Netlify / Cloudflare Pages | Next.js 原生支持、edge 网络 |
| **数据库** | SQLite（应用内嵌）+ S3 备份 | Postgres / Turso | 学生用、数据量小、零运维 |
| **监控指标** | Grafana Cloud | Datadog / New Relic | 免费 10k metrics、Prometheus 生态 |
| **日志** | Better Stack (Logtail) | Loki / Datadog Logs | 简单查询、价格透明 |
| **错误追踪** | Sentry | Rollbar / Bugsnag | 免费 5k events/月、前端 SDK 完善 |
| **APM** | Grafana Pyroscope | Datadog APM | 火焰图定位慢函数 |
| **告警** | Grafana Alerting + Slack Webhook | PagerDuty / OpsGenie | 免费、Slack 集成 |
| **依赖扫描** | Dependabot + Trivy | Snyk | GitHub 原生 |
| **密钥管理** | 1Password CLI / Doppler | HashiCorp Vault | 团队友好、Doppler 同步 .env |
| **域名** | Namecheap + Cloudflare | Route 53 | Cloudflare 代理免费 |
| **HTTPS** | Cloudflare | Let's Encrypt | 自动 + 免费 |
| **CI 缓存** | GitHub Actions Cache | 自建 S3 | 集成好 |
| **E2E** | Playwright | Cypress | 多浏览器、稳定 |
| **压测** | locust | k6 / Apache JMeter | Python、CI 集成好 |
| **AI 评估** | 自建 + LLM-as-judge | DeepEval / Promptfoo | 灵活、成本低 |
| **代码质量** | ruff (Python) + ESLint (TS) | pylint / tslint | 快、规则全 |
| **类型检查** | mypy (Python) + tsc (TS) | pyright | 标准 |

### 3.2 为什么选 Railway + Vercel（不用自建 K8s）

| 维度 | Railway | 自建 K8s |
|------|---------|---------|
| 启动时间 | 5 分钟 | 2-3 天 |
| 月度成本 | $5-20 | $200+ |
| 运维负担 | 极低 | 高 |
| 弹性 | 自动 | 手动 |
| 适合规模 | < 1万 QPS | > 1万 QPS |
| **本项目** | ✅ 适合（学生用，流量低） | ❌ 过度 |

**结论**：PaaS 是这个项目**当前阶段**的最佳选择。流量超过 1万 QPS 后再考虑迁 K8s。

### 3.3 服务清单（v3.2 状态）

| 服务 | 平台 | 规格 | 月成本 | 状态 |
|------|------|------|--------|------|
| 后端 (FastAPI) | Railway | 1 instance, 1GB RAM | $5 | 待部署 |
| 前端 (Next.js) | Vercel | Free tier | $0 | 待部署 |
| 数据库 (SQLite) | Railway Volume | 1GB | 含在 Railway | 待部署 |
| Pinecone | Pinecone Serverless | 1 index, 841 vectors | $0 (免费) | ✅ 已用 |
| MiniMax M3 | MiniMax Token Plan | ~0.5B tokens/月 | 已订阅 | ✅ 已用 |
| 监控 | Grafana Cloud | 10k metrics | $0 (免费) | 待配 |
| 错误追踪 | Sentry | 5k events/月 | $0 (免费) | 待配 |
| 日志 | Better Stack | 1GB/月 | $0 (免费) | 待配 |
| 域名 | Namecheap | 1 个 | $10/年 | 待买 |
| **合计** | | | **~$10-15/月** | |

---

## 4. 监控、日志与告警

### 4.1 三大支柱

```
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │   METRICS    │    │     LOGS     │    │    TRACES    │
  │  (Grafana)   │    │(Better Stack)│    │   (Sentry)   │
  │              │    │              │    │              │
  │ • 延迟       │    │ • 请求/响应 │    │ • 异常堆栈   │
  │ • 错误率     │    │ • 业务事件   │    │ • 用户会话   │
  │ • 资源占用   │    │ • 慢查询     │    │ • 前端报错   │
  │ • 业务指标   │    │ • M3 token   │    │ • 性能追踪   │
  └──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                       ┌──────────────┐
                       │   ALERTING   │
                       │  (Grafana →  │
                       │   Slack)     │
                       └──────────────┘
```

### 4.2 SLI / SLO 定义

**SLI（Service Level Indicator）— 实际指标**：

| SLI | 测量方法 | 当前基线 | 目标 |
|------|---------|---------|------|
| API 可用性 | 1 - (5xx / 总请求) | 待测 | ≥ 99.5% |
| 聊天 P95 延迟 | 95th percentile of /api/chat/* latency | 8s | ≤ 8s |
| 出题 P95 延迟 | 95th percentile of /api/quiz/generate | 15s | ≤ 15s |
| 出题成功率 | 1 - (出题 500 / 总出题) | 80% | ≥ 90% |
| Pinecone 查询 P95 | histogram_quantile(0.95, ...) | 200ms | ≤ 300ms |

**SLO（Service Level Objective）— 目标值**：
- 月度 uptime ≥ 99.5%（每月允许 ≤ 3.6 小时停机）
- 用户能正常使用核心功能的概率 ≥ 99%

### 4.3 关键指标（按优先级）

#### 必须有（否则不能上线）
1. **请求 QPS + 错误率**（按端点分）
2. **延迟 P50/P95/P99**（按端点）
3. **CPU + 内存使用率**
4. **健康检查状态**
5. **M3 token 消耗**（成本控制）
6. **M3 retry 率 + 截断率**（质量问题信号）
7. **Pinecone 错误率**

#### 应该有（上线后 1 周内补）
8. **业务指标**：DAU、对话轮数、出题数
9. **前端 Web Vitals**：FCP、LCP、CLS
10. **认证失败率**（暴力破解信号）
11. **慢 SQL / 慢 API top 10**

#### 锦上添花（一个月内补）
12. **用户分群指标**（按学段/学校）
13. **A/B 测试面板**（prompt 优化对比）
14. **资源成本仪表板**（Railway / Pinecone / M3）

### 4.4 关键告警规则

| 告警 ID | 名称 | 条件 | 持续 | 级别 | 动作 |
|--------|------|------|------|------|------|
| A-01 | API 完全挂 | 5xx > 50% | 2min | P0 | 电话 oncall |
| A-02 | API 部分挂 | 5xx > 5% | 5min | P1 | Slack #oncall |
| A-03 | 慢 | P95 > 2× baseline | 10min | P1 | Slack #oncall |
| A-04 | M3 配额 50% | token 累计 ≥ 月预算 50% | 即时 | P2 | Slack #ops |
| A-05 | M3 配额 90% | token 累计 ≥ 月预算 90% | 即时 | P1 | Slack #oncall |
| A-06 | 磁盘 80% | disk > 80% | 5min | P2 | 邮件 |
| A-07 | 磁盘 95% | disk > 95% | 1min | P1 | Slack #oncall |
| A-08 | 健康检查失败 | 连续 3 次 30s | 1.5min | P0 | 自动重启 + 通知 |
| A-09 | 出题成功率低 | success rate < 70% | 30min | P1 | 触发 prompt 优化 |
| A-10 | Pinecone 错误 | 5xx from Pinecone > 0 | 5min | P2 | Slack #ops |

### 4.5 日志规范

#### 4.5.1 结构化日志（JSON）

后端用 `structlog`：
```python
import structlog
logger = structlog.get_logger()

logger.info("chat_completed",
    user_id=123,
    session_id=456,
    latency_ms=3200,
    tokens_in=1250,
    tokens_out=939,
    mode="grammar",
    sources_count=5,
)
```

#### 4.5.2 必须记录的字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `timestamp` | ISO8601 | `2026-06-02T05:30:00Z` |
| `level` | INFO/WARN/ERROR | `INFO` |
| `event` | 事件名（snake_case） | `chat_completed` |
| `trace_id` | 请求追踪 ID | `abc123` |
| `user_id` | 用户 ID（登录用户） | `42` |
| `latency_ms` | 耗时 | `3200` |
| `endpoint` | API 路径 | `/api/chat/stream` |
| `status` | HTTP 状态 | `200` |
| `error` | 异常（如果有） | `ValueError: ...` |

#### 4.5.3 不能记录的（隐私）

- ❌ 用户密码
- ❌ JWT token 完整值（只记 hash 前 8 位）
- ❌ 学生的真实姓名/学校（即使在 user 表中）
- ❌ 用户上传文件的完整内容（只记 metadata）

### 4.6 Sentry 错误追踪

**前端集成**：
```typescript
// frontend/lib/sentry.ts
import * as Sentry from "@sentry/nextjs";
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,    // 10% 性能追踪
  beforeSend(event) {
    // 脱敏
    if (event.user) delete event.user.ip_address;
    return event;
  },
});
```

**后端集成**：
```python
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,
    environment=os.getenv("APP_ENV", "production"),
)
```

**告警关联**：
- Sentry 新 issue → 自动创建 Slack 频道
- 高频 error（> 10/min）→ 自动 @oncall

### 4.7 OnCall 轮值

| 角色 | 工具 | 频率 |
|------|------|------|
| OnCall Primary | PagerDuty 排班 | 1 周轮换 |
| OnCall Secondary | PagerDuty | 同上 |
| 业务方 SLA 联系人 | 维护名单 | - |

**首次 oncall 上岗 checklist**：
- [ ] 已加入 #oncall Slack 频道
- [ ] 已下载 PagerDuty App
- [ ] 已读所有 Runbook（`docs/runbooks/`）
- [ ] 已能 SSH 到生产服务器
- [ ] 已了解如何回滚最新 release

---

## 5. 事件响应与 Runbook

### 5.1 事件分级

| 级别 | 影响 | 例子 | 响应 SLA | 解决 SLA |
|------|------|------|---------|---------|
| **P0** | 核心功能全挂 | API 5xx > 50% | 30 min | 4h |
| **P1** | 部分功能受损 | 出题失败、Pinecone 不可用 | 1h | 24h |
| **P2** | 体验下降但有 workaround | UI 错位、慢查询 | 4h | 1 周 |
| **P3** | 改进项 | 文案错、优化建议 | 下次 sprint | 不限 |

### 5.2 事件响应流程

```
告警触发
  ↓
1. 确认（oncall 在 5min 内 ack 告警）
  ↓
2. 分级（按 §5.1 表）
  ↓
3. 通知（按级别）
  ↓
4. 止血（短期恢复 — 重启/回滚/限流）
  ↓
5. 根因（深挖）
  ↓
6. 永久修复
  ↓
7. 复盘（postmortem）
```

### 5.3 P0 响应剧本

```yaml
P0 - API 完全不可用:
  立即动作 (5min):
    - oncall ack 告警
    - 看 Railway 状态: railway status
    - 看 Sentry 错误: sentry.io/issues
    - 决定: rollback or hotfix

  5-15min:
    - Slack #englishmaster: "我们正在处理 P0 故障，预计 30min 恢复"
    - 如果是代码问题: railway rollback --to v3.2
    - 如果是依赖问题: 检查 Pinecone / M3

  15-30min:
    - 健康检查: curl /api/health
    - 通知业务方当前状态

  30min-4h:
    - 根因 + 修复
    - 部署修复
    - 监控 1h 无异常

  4h-24h:
    - 写 postmortem (无指责)
    - 跟踪改进项
```

### 5.4 常见 Runbook（高频故障）

#### RB-01：M3 API 不可用

**症状**：
- 所有对话/出题/批改返回 5xx
- 错误日志含 `M3 API timeout` 或 `ConnectionError`

**根因可能**：
- MiniMax 服务故障
- 网络断
- API key 过期/欠费

**排查**：
```bash
# 1. 直接 curl 测试
curl -X POST https://api.minimax.io/v1/chat/completions \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M3","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
# 期望：200 OK

# 2. 看后端日志
railway logs | grep "minimax"
```

**缓解**：
- 短期：在前端显示"AI 暂时不可用，请稍后重试"
- 长期：增加多个 AI provider fallback

---

#### RB-02：Pinecone 不可用

**症状**：
- 所有对话返回"未找到相关内容"或空 sources
- 后端日志含 `PineconeApiException` 或 `timeout`

**排查**：
```bash
# 1. 直接测试
curl -H "Api-Key: $PINECONE_API_KEY" \
  https://xsjkndb01-f408jww.svc.aped-4627-b74a.pinecone.io/describe_index_stats
# 期望：{"dimension":1024,"total_vector_count":841,...}

# 2. 看后端是否连得上
railway logs | grep -i "pinecone"
```

**缓解**：
- 短期：RAG 降级为"无上下文"模式（但仍回答）
- 长期：缓存最近 100 个 query 的 RAG 结果

---

#### RB-03：SQLite 损坏

**症状**：
- 用户登录失败（500）
- 错误日志含 `database is locked` 或 `disk I/O error`

**排查**：
```bash
# 1. SSH 到生产
railway shell

# 2. 查 DB
sqlite3 database/app.db "PRAGMA integrity_check;"
# 期望：ok

# 3. 看磁盘
df -h
```

**恢复**：
```bash
# 1. 停服务
# 2. 拉备份
aws s3 cp s3://englishmaster-backups/db-2026-06-01.db database/app.db
# 3. 重启服务
# 4. 验证
curl /api/health
```

---

#### RB-04：磁盘满

**症状**：
- 健康检查失败
- Sentry 报 `No space left on device`

**排查 + 缓解**：
```bash
df -h
du -sh /tmp/*  # 临时文件
# 清 log
journalctl --vacuum-time=3d
# 清 pip cache
pip cache purge
# 扩大磁盘（Railway 一键）
railway volume extend
```

---

#### RB-05：出题/批改 5xx

**症状**：
- 用户在 /quiz 看到错误
- Sentry 报 `parse_json_response failed` 或 `max_tokens`

**排查**：
```bash
# 看后端日志，找失败的 prompt
railway logs | grep -A 20 "parse_json_response failed"
```

**缓解**：
- 短期：前端"重试"按钮
- 中期：减少 max_tokens、提高 RAG top_k
- 长期：改用更稳定的 prompt + 双模型备份

### 5.5 Postmortem 模板

**文件位置**：`docs/postmortem/YYYY-MM-DD-{title}.md`

```markdown
# Postmortem: {事件简述}

**日期**：YYYY-MM-DD
**级别**：P0
**影响**：X 个用户，Y 小时
**负责人**：@xxx

## 时间线
- HH:MM 告警触发
- HH:MM oncall 确认
- HH:MM 根因定位
- HH:MM 临时缓解
- HH:MM 修复上线
- HH:MM 完全恢复

## 根因
（详细说明）

## 影响
- 用户量：X
- 持续时间：Y
- 业务损失：¥Z

## 为什么没拦住
（事后分析）

## 改进项
| 改进 | 负责人 | 截止 |
|------|--------|------|
| 加 x 监控 | @xxx | MM-DD |
| 优化 y 代码 | @xxx | MM-DD |

## 教训
（无指责，归因于系统而非个人）
```

---

## 6. 备份与灾难恢复

### 6.1 数据资产清单

| 资产 | 重要性 | 大小 | 持久性要求 |
|------|--------|------|----------|
| 代码 (GitHub) | 极高 | MB | 永久 |
| 文档 (GitHub) | 极高 | MB | 永久 |
| .env + Secrets | 极高 | KB | 永久 |
| Pinecone vectors | 高 | 50MB | 永久（可重建） |
| raw_pages JSON | 高 | 50MB | 永久（重跑 OCR 基准） |
| SQLite 数据库 | **高**（含用户数据） | 1-100MB | 永久 |
| 用户上传 PDF/图片 | 中 | 0-1GB | 1 年 |
| 日志 | 低 | 1-10GB/月 | 30 天 |
| 监控历史 | 低 | 自动清理 | 90 天 |

### 6.2 备份策略

#### 6.2.1 SQLite 备份（每天 03:00 UTC）

```bash
#!/bin/bash
# /opt/backup/sqlite.sh
DB_PATH="/app/database/app.db"
BACKUP_DIR="/backups/sqlite"
S3_BUCKET="s3://englishmaster-backups/sqlite"
RETENTION_DAYS=30

# 1. 触发 SQLite 备份（不锁表）
sqlite3 $DB_PATH ".timeout 30000" ".backup $BACKUP_DIR/app-$(date +%Y%m%d).db"

# 2. 上传到 S3
aws s3 cp $BACKUP_DIR/app-$(date +%Y%m%d).db $S3_BUCKET/ \
  --storage-class STANDARD_IA

# 3. 清理本地 > 7 天的
find $BACKUP_DIR -name "app-*.db" -mtime +7 -delete

# 4. 清理 S3 > 30 天的
aws s3api list-objects-v2 --bucket englishmaster-backups \
  --query "Contents[?LastModified<=\`$(date -d '30 days ago' -Iseconds)\`].Key" \
  | jq -r '.[]?' | xargs -I {} aws s3 rm s3://englishmaster-backups/{}
```

**调度**：cron `0 3 * * * /opt/backup/sqlite.sh`

**监控**：备份成功发 Slack 通知；连续 2 天失败发 P1 告警。

#### 6.2.2 Pinecone 备份（每周）

```bash
# 1. 导出 vector IDs 和 metadata
python scripts/backup_pinecone.py > /backups/pinecone/ids-$(date +%Y%m%d).json

# 2. 上传到 S3
aws s3 cp /backups/pinecone/ s3://englishmaster-backups/pinecone/ --recursive
```

**真正的 vector 数据**由 Pinecone 自身冗余存储（Serverless 自动 3 副本），我们只需保存 ID 列表以便重建。

#### 6.2.3 Secrets 备份

- **1Password** 自动云端同步
- **Doppler** 自动版本化（每次变更留痕）
- **本地导出**到 S3 加密桶：`./secrets-{date}.tar.gz.gpg`

#### 6.2.4 用户数据导出

用户有导出权（GDPR-like）：

```bash
# 用户申请"导出我的数据"
python scripts/export_user_data.py --user-id 123 \
  --output /tmp/user-123-export.zip
# 包含：chats.json, quiz_records.csv, vocab_progress.csv
```

### 6.3 灾难恢复

#### 6.3.1 场景模拟（每季度演练一次）

| 场景 | 恢复源 | 预计 RTO | 实际演练日期 |
|------|--------|---------|------|
| DB 损坏 | S3 备份 | ≤ 1h | 下次演练：Q3 |
| Pinecone 删库 | 重跑 03 脚本 | ≤ 4h | 下次演练：Q3 |
| 整个 Railway 挂 | 切到 Render 备份 | ≤ 8h | 下次演练：Q4 |
| 代码仓库误删 | GitHub 恢复 | ≤ 24h | 演练难度高，年度一次 |
| Secrets 泄露 | 全部轮换 + deploy | ≤ 4h | 演练：Q3 |

#### 6.3.2 恢复命令速查

```bash
# 场景 1：DB 损坏
railway shell
# 停服务（Railway 自动重启会失败，但先停避免请求打到损坏的 DB）
# 拉备份
aws s3 cp s3://englishmaster-backups/sqlite/app-20260601.db /app/database/app.db
exit  # Railway 重启服务

# 场景 2：Pinecone 重建
python scripts/03_embed_and_upload.py
# 全自动重跑，约 5min

# 场景 3：完整恢复
# 1. 克隆代码
git clone git@github.com:xsj/junior-english-agent.git
# 2. 恢复 secrets
op inject -i .env.template -o .env
# 3. 启动服务
docker compose up -d
# 4. 验证
curl /api/health
```

### 6.4 RTO / RPO 目标

| 资产 | RPO（数据丢失容忍） | RTO（恢复时间） |
|------|---------------------|-----------------|
| 用户对话/进度 | ≤ 24h（每日备份） | ≤ 4h |
| Pinecone | ≤ 7d（重跑需要 raw_pages） | ≤ 4h |
| 代码 | 0 | ≤ 1h |
| Secrets | 0 | ≤ 1h |

---

## 7. 成本估算

### 7.1 月度运营成本（学生用规模，~100 DAU）

| 项目 | 平台 | 规格 | 单价 | 月成本 |
|------|------|------|------|--------|
| 后端 | Railway | 1 instance, 1GB RAM | $5 | $5 |
| 前端 | Vercel | Free tier | $0 | $0 |
| 数据库 | Railway Volume | 1GB | $1 | $1 |
| Pinecone | Serverless | 1 index, ~1k vectors | 免费 | $0 |
| MiniMax M3 | Token Plan | ~30M tokens/月 | 0.5B tokens 配额 $20 | $20（订阅） |
| 域名 | Namecheap | 1 个 | $10/年 | $1 |
| Cloudflare | 免费 | - | $0 | $0 |
| Grafana Cloud | Free | 10k metrics | $0 | $0 |
| Sentry | Free | 5k events | $0 | $0 |
| Better Stack | Free | 1GB logs | $0 | $0 |
| GitHub | Free | 公开仓库 | $0 | $0 |
| **合计** | | | | **~$27/月** |

### 7.2 流量增长下的成本曲线

| 规模 | DAU | API 调用/月 | 后端 | M3 token/月 | 月总成本 |
|------|-----|------------|------|------------|----------|
| 早期 | 50 | 5k | $5 | 5M | ~$15 |
| 学生用 | 100 | 20k | $5 | 20M | ~$27 |
| 小机构 | 500 | 100k | $20 | 100M | ~$150 |
| 中机构 | 2000 | 500k | $80 | 500M | ~$600 |
| 大机构 | 10k+ | 3M+ | 自建 K8s | 1B+ | $2000+ |

**关键拐点**：DAU > 500 或 M3 月 token > 200M 时，需重新评估。

### 7.3 成本优化策略

1. **缓存**：常见查询 RAG 结果缓存 1h（节省 ~30% token）
2. **prompt 优化**：更短的 prompt = 更少 token（已完成 30%）
3. **流式响应**：用户读第 1 段就 cancel 时，节省 output token
4. **max_tokens 限值**：出题 3000、对话 2048、批改 600
5. **降级策略**：M3 配额耗尽时 fallback 到本地更小模型

---

## 8. 安全与合规

### 8.1 威胁模型

| 威胁 | 攻击者 | 动机 | 可能性 |
|------|--------|------|--------|
| API Key 泄露 | 内部/外部 | 滥用配额、刷数据 | 中 |
| 用户暴力破解 | 外部 | 账号入侵 | 中 |
| SQL 注入 | 外部 | 拖库 | 低（用 ORM） |
| XSS | 外部 | 窃 cookie | 中（前端） |
| CSRF | 外部 | 越权操作 | 低（无 cookie，用 JWT） |
| 中间人 | 外部 | 窃听 | 低（HTTPS） |
| 拒绝服务 | 外部 | 瘫痪服务 | 中 |
| 内部滥用 | 员工 | 偷数据 | 低 |

### 8.2 关键安全措施

#### 8.2.1 Secrets 管理

- **绝不允许** secrets 进 Git（已用 `.gitignore` + 预提交 hook）
- 全部 secrets 在 1Password 或 Doppler 集中管理
- 部署时通过环境变量注入（Railway Secrets / Vercel Env Vars）
- 定期轮换：API Key 90 天，JWT Secret 180 天
- **绝不允许**在日志中打印完整 token / 密码

#### 8.2.2 认证安全

- 密码用 `hashlib.sha256(salt + password)` 存储（待升级到 bcrypt/argon2）
- JWT 用 HS256，secret ≥ 32 字节
- Token 有效期 30 天（可缩短）
- 所有受保护接口 `Depends(get_current_user)`
- 登录失败统一返回 401（不暴露用户是否存在）
- 登录限流：同 IP 5 分钟 ≤ 10 次（待实现）

#### 8.2.3 HTTPS / 传输安全

- Cloudflare 代理 + 自动 SSL
- 强制 HTTPS（Strict-Transport-Security 头）
- 禁用过时协议（TLS 1.0/1.1）

#### 8.2.4 前端安全

- React 自动转义（无 dangerouslySetInnerHTML）
- 用户输入不直接拼 HTML
- react-markdown 渲染 AI 输出（潜在 XSS 风险，需配 sanitizer）
- CORS：限定具体 origin，不用 `*`

#### 8.2.5 数据库安全

- SQLAlchemy ORM 参数化查询（无 SQL 注入）
- 用户表密码 hash
- JWT secret 不入 DB

### 8.3 依赖扫描

```bash
# 后端
pip install pip-audit
pip-audit

# 前端
cd frontend
npm audit
```

**触发**：CI 每次 push 自动跑。**门槛**：0 个 P0/P1 漏洞才能合 PR。

### 8.4 镜像扫描

```bash
# 推镜像时
trivy image ghcr.io/xsj/backend:v3.3
```

**门槛**：CRITICAL 漏洞 = 0 才能部署。

### 8.5 合规清单

| 项 | 状态 | 备注 |
|------|------|------|
| 用户数据加密存储 | ⏳ 部分 | SQLite 未加密（应用层加解密待补） |
| 用户数据导出权 | ✅ 脚本就绪 | `scripts/export_user_data.py` |
| 用户数据删除权 | ✅ SQLAlchemy cascade | 删 user 触发 |
| Cookie 隐私声明 | ❌ 待加 | 生产前必做 |
| 服务条款 | ❌ 待写 | 生产前必做 |
| 隐私政策 | ❌ 待写 | 生产前必做 |
| 第三方依赖清单 | ✅ 自动 | `requirements.txt` + `package.json` |
| 儿童在线隐私（COPPA） | ⚠️ 关注 | 用户 < 13 岁时需家长同意 |
| 数据驻留 | ✅ 国内用户 | Pinecone AWS us-east-1，国内需关注 |

### 8.6 渗透测试

- **首次上线前**：雇第三方做一次完整渗透测试
- **之后**：每年一次 + 重大变更后

---

## 9. 变更与发布管理

### 9.1 变更分类

| 类型 | 例子 | 流程 |
|------|------|------|
| 紧急 (P0) | P0 bug、安全漏洞 | 紧急 PR → 1 人 review → 直接 merge |
| 标准 | 新功能、bug 修复 | PR → CI → 2 人 review → 灰度 |
| 计划 | 重大重构、依赖升级 | RFC 文档 → 团队 review → 计划发布窗口 |

### 9.2 发布窗口

| 环境 | 频率 | 窗口 |
|------|------|------|
| 开发 | 随时 | - |
| Staging | 自动（merge main） | - |
| 生产 | 每周二/四 10:00 | 30min 灰度 |

**禁止发布日**：周五、周末、节假日前一天。

### 9.3 发布流程

```
1. 提 PR（含 changelog）
   ↓
2. CI 全过（测试、lint、扫描）
   ↓
3. 2 人 review
   ↓
4. merge main → 自动 deploy staging
   ↓
5. 运维手动 trigger 生产灰度
   ↓
6. 30min 观察
   ↓
7. 100% 切量
   ↓
8. Slack 通知
   ↓
9. 持续 24h 监控
```

### 9.4 版本号规范

[SemVer](https://semver.org/lang/zh-CN/)：
- **MAJOR**：不兼容 API 变更
- **MINOR**：新功能、向后兼容
- **PATCH**：bug 修复

例：`v3.3.0` — Phase 7+ 完成、bug fix 多项。

**Tag 命令**：
```bash
git tag -a v3.3.0 -m "Phase 7+ conversation mode tags + 4 bug fixes"
git push origin v3.3.0
# GitHub Action 自动 build Docker 镜像 + deploy
```

### 9.5 Changelog

**位置**：`docs/CHANGELOG.md`

```markdown
# Changelog

## v3.3.0 (2026-06-XX)
### Added
- Phase 7+ conversation mode tags
- §7.5 RAG top_k decision log

### Fixed
- 修了 OCR Unit 125 误识别 #23
- 修了 grade 中文双引号破坏 JSON #24

## v3.2.0 (2026-06-02)
...
```

### 9.6 回滚 Runbook

**何时回滚**（见 §5.3 P0 流程）：
- 健康检查连续 3 次失败
- 错误率 > 5%
- P95 > 2× baseline
- 任何 P0 报告

**回滚命令**：
```bash
# Railway
railway rollback --to v3.2

# Vercel
vercel rollback

# 或在 GitHub:
# 1. Revert PR
# 2. Auto-deploy
```

**回滚后必做**：
- Slack 通知"已回滚到 v3.2"
- 24h 内写 postmortem
- 加回归测试

---

## 10. 运维待办（Roadmap）

### P1（1-2 周内必做）

- [ ] GitHub 仓库创建 + 分支保护
- [ ] 配 GitHub Secrets
- [ ] 买域名 + Cloudflare 代理
- [ ] Railway 后端部署（最小配置）
- [ ] Vercel 前端部署
- [ ] GitHub Actions CI（跑测试）
- [ ] 配 Grafana Cloud 监控
- [ ] 配 Sentry 错误追踪
- [ ] SQLite 每日备份脚本
- [ ] oncall 文档 + 排班

### P2（1 个月内做）

- [ ] Playwright E2E
- [ ] 性能压测 baseline
- [ ] AI 评估集 30+ 条
- [ ] 灰度发布脚本
- [ ] Log 聚合（Better Stack）
- [ ] Dependabot 自动更新
- [ ] Docker 镜像化
- [ ] 健康检查 endpoint 加详细诊断
- [ ] Slack 集成告警
- [ ] Postmortem 模板

### P3（季度内做）

- [ ] Alembic 数据库迁移
- [ ] 密钥管理（Doppler / 1Password CLI）
- [ ] 多区域部署（failover）
- [ ] 用户数据加密
- [ ] 合规文档（隐私政策、服务条款）
- [ ] 渗透测试
- [ ] 监控面板优化（业务指标）
- [ ] A/B 测试框架（prompt 优化对比）
- [ ] RAG 评估脚本
- [ ] 自动化灾难恢复演练

### 长期（半年以上）

- [ ] 自建 K8s（如果 DAU > 1k）
- [ ] 国际化（多语言支持）
- [ ] 多租户架构（不同学校/机构隔离数据）
- [ ] AI 模型微调（如果评估显示 base 不够）
- [ ] 移动 App（React Native / Flutter）

---

## 附录 A：每周 OnCall Checklist

```markdown
## 周一检查
- [ ] 备份完整性：S3 上有上周 7 天的 SQLite 备份
- [ ] 监控面板：上周错误率、延迟趋势无异常
- [ ] 依赖更新：Dependabot PRs 都 review 了
- [ ] 成本：M3 token 用量在预算内
- [ ] 容量：磁盘 < 70%

## 每日检查（自动化）
- 健康检查 (/api/health)
- 5xx 错误率 < 0.5%
- P95 延迟 < 2× baseline
- 备份成功通知
- M3 配额用量
```

## 附录 B：必备文件清单

- [ ] `docs/OPS_PLAN.md`（本文件）
- [ ] `docs/TEST_PLAN.md`（测试计划）
- [ ] `docs/CHANGELOG.md`（变更日志）
- [ ] `docs/runbooks/RB-01-..RB-05-*.md`（5 个 Runbook）
- [ ] `docs/postmortem/`（事故复盘）
- [ ] `docs/architecture/`（架构图）
- [ ] `.github/workflows/ci.yml`
- [ ] `.github/workflows/deploy.yml`
- [ ] `Dockerfile` (backend)
- [ ] `frontend/Dockerfile`
- [ ] `docker-compose.yml`
- [ ] `scripts/backup/sqlite.sh`
- [ ] `scripts/backup/pinecone.py`
- [ ] `scripts/export_user_data.py`

---

*文档版本：v1.0 | 状态：待评审*
*配套文档：[README.md](../README.md) · [TEST_PLAN.md](./TEST_PLAN.md) · [AGENTS.md](../AGENTS.md) · [开发文档](./初中英语AI学习Agent开发文档.md)*
