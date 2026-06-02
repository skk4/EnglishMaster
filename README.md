# EnglishMaster Agent

> 八年级英语 AI 智能学习助手 — 基于 RAG + 大模型的本地全栈应用

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/) [![Next.js](https://img.shields.io/badge/Next.js-14.2-black)](https://nextjs.org/) [![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE) [![Tests](https://img.shields.io/badge/Tests-17%20passing-brightgreen)]() [![PRs](https://img.shields.io/badge/PRs-welcome-orange)](./CONTRIBUTING.md)

> 📖 [完整文档](./docs/) | 🧪 [测试计划](./docs/TEST_PLAN.md) | 🚀 [运维计划](./docs/OPS_PLAN.md) | 📊 [产品计划](./docs/PM_PLAN.md)

---

## 快速体验（30 秒）

```bash
git clone https://github.com/xsj/junior-english-agent.git
cd junior-english-agent
cp .env.example .env
# 编辑 .env 填入 MINIMAX_API_KEY 和 PINECONE_API_KEY

make install
make dev     # 终端 1 启后端，终端 2 启前端
```

浏览器打开 `http://localhost:3000`。

## 项目架构

```
用户浏览器
  ↓ HTTP
Next.js 前端 (Vercel)
  ↓ REST + SSE
FastAPI 后端 (Railway)
  ├─→ RAG: Pinecone/FAISS/Qdrant
  ├─→ AI: MiniMax M3 (OpenAI 兼容)
  └─→ DB: SQLite
```

**当前状态**：v3.2，7 阶段开发完成（数据 → 后端 → 出题 → 前端 → 进度 → 多用户 → 模式标签），跑通端到端。

---

## 项目简介

EnglishMaster 是一款面向**人教版八年级英语**（Go for it!）的 AI 学习助手。它把教材的扫描件转化成结构化知识库，让学生可以通过自然语言对话进行课文问答、语法讲解、词汇练习和随堂测试，所有回答都基于教材原文并附带来源引用。

### 核心能力

| 模块 | 能力 |
|------|------|
| 📖 **课文问答** | 基于教材内容的 RAG 问答，附带来源单元/页码 |
| 📝 **语法讲解** | 4 种模式（通用/语法/出题/对话），结合教材例句解释 |
| 💬 **对话历史** | 多会话持久化（SQLite），刷新/切换/跨设备不丢失；每条消息标注使用的模式（通用/语法/出题/对话） |
| 🧪 **随堂测试** | AI 自动出题（单选/填空/翻译），自动批改并给出解析 |
| 🔤 **词汇闪卡** | 从教材提取词汇表，翻卡式记忆 |
| 📊 **学习进度** | 个人做题统计、正确率、薄弱单元 Top 3 |
| 👥 **多用户** | 注册/登录/JWT 认证，进度和会话按用户隔离 |

---

## 技术栈

| 层级 | 选型 | 版本 |
|------|------|------|
| Python | CPython | 3.11.x |
| Web 框架 | FastAPI | 0.115+ |
| ASGI 服务器 | Uvicorn | 0.30+ |
| 数据库 | SQLite + aiosqlite | — |
| ORM | SQLAlchemy | 2.0+ (async) |
| Embedding | sentence-transformers | 5.x |
| 向量数据库 | Pinecone | xsjkndb01 (1024维) |
| 大模型 | MiniMax M3（OpenAI 兼容接口）| — |
| 前端框架 | Next.js | 14.2 (App Router) |
| 前端语言 | TypeScript | 5.x |
| CSS | Tailwind CSS | 3.x |

**关键依赖**：`pymupdf`（PDF 处理）、`easyocr`（OCR 备选）、`openai`（调 MiniMax 兼容接口）、`pyjwt`（认证）。

---

## 目录结构

```
junior_english_agent/
├── AGENTS.md                              # 开发规范（必读）
├── CLAUDE.md                              # Claude Code 入口
├── README.md                              # 本文件
│
├── data/                                  # 数据目录
│   ├── raw/                               # 原始 PDF
│   │   ├── grade8_semester1.pdf           # 上册（原生 PDF，10.2MB）
│   │   └── grade8_semester2.pdf           # 下册（扫描版，230.6MB）
│   ├── images/                            # PDF 转出的 PNG
│   │   ├── semester1/                     # 暂无（原生 PDF 未转图）
│   │   └── semester2/                     # 146 张 PNG
│   ├── ocr_cache/                         # OCR 缓存（断点续传）
│   ├── processed/                         # 处理后数据
│   │   ├── raw_pages_semester1.json
│   │   ├── raw_pages_semester2.json
│   │   ├── chunks_semester1.json          # 362 chunks
│   │   └── chunks_semester2.json          # 479 chunks
│   └── vocab/                             # 教材词汇表
│       ├── vocab_semester1.json           # 22 words
│       └── vocab_semester2.json           # 92 words
│
├── scripts/                               # 数据处理流水线
│   ├── 00a_pdf_to_images.py               # PDF → 图片 / 原生提取
│   ├── 00b_ocr_with_minimax.py            # MiniMax M3 OCR
│   ├── 00c_verify_ocr.py                  # OCR 质量验证
│   ├── 02_chunk_text.py                   # 文本分块
│   ├── 03_embed_and_upload.py             # 向量化 + 上传 Pinecone
│   ├── 04_verify_pinecone.py              # 检索验证
│   └── extract_vocab.py                   # 提取教材词汇
│
├── backend/                               # FastAPI 后端
│   ├── main.py                            # FastAPI 入口
│   ├── config.py                          # 配置管理
│   ├── dependencies.py                    # 全局单例（model/pinecone/jwt）
│   ├── models/
│   │   ├── request_models.py              # Pydantic 请求模型
│   │   └── db_models.py                   # SQLAlchemy ORM（User/QuizRecord/VocabProgress/ChatSession/ChatMessage）
│   ├── services/
│   │   ├── rag_service.py                 # RAG 检索
│   │   ├── agent_service.py               # 对话 Agent
│   │   ├── quiz_service.py                # 出题/批改
│   │   ├── progress_service.py            # 进度统计
│   │   ├── vocab_service.py               # 词汇查询
│   │   └── auth_service.py                # 认证 + JWT
│   ├── routers/
│   │   ├── auth.py                        # /api/auth/*
│   │   ├── chat.py                        # /api/chat/*
│   │   ├── history.py                     # /api/history/*
│   │   ├── quiz.py                        # /api/quiz/*
│   │   ├── progress.py                    # /api/progress/*
│   │   └── vocabulary.py                  # /api/vocab/*
│   └── prompts/
│       ├── system_prompt.py               # 系统提示词（4 种 mode）
│       └── quiz_prompt.py                 # 出题/批改 prompt
│
├── frontend/                              # Next.js 前端
│   ├── app/
│   │   ├── page.tsx                       # 聊天主页（/）
│   │   ├── login/page.tsx                 # 登录/注册
│   │   ├── quiz/page.tsx                  # 随堂测试
│   │   ├── vocabulary/page.tsx            # 词汇闪卡
│   │   └── progress/page.tsx              # 学习进度
│   ├── components/
│   │   ├── chat/                          # MessageBubble / SourcePanel / InputBar
│   │   └── quiz/                          # QuizCard
│   ├── hooks/
│   │   ├── useChat.ts                     # 聊天状态管理
│   │   └── useAuth.ts                     # 路由守卫
│   └── lib/
│       ├── api.ts                         # API 客户端（含 SSE 解析）
│       ├── auth.ts                        # token 管理
│       └── types.ts                       # TypeScript 类型
│
├── database/                              # SQLite 文件位置
│   └── app.db                             # 运行时自动生成
│
├── docs/
│   └── 初中英语AI学习Agent开发文档.md      # 完整开发文档
│
└── .env                                   # 环境变量（不提交 git）
```

---

## 快速启动

### 前置要求

- macOS 13+ / Linux
- Python 3.11.x（推荐 pyenv）
- Node.js 18+ / npm
- 已创建的 Pinecone Index `xsjkndb01`（1024维，us-east-1）
- 已注册的 MiniMax Token Plan（含 `MINIMAX_API_KEY`）

### 1. 克隆与虚拟环境

```bash
git clone <repo-url> && cd junior_english_agent
python3 -m venv .venv
source .venv/bin/activate

# 安装后端依赖
pip install fastapi 'uvicorn[standard]' anthropic openai pyjwt[crypto] \
            pinecone sentence-transformers torch \
            pymupdf sqlalchemy aiosqlite 'pydantic-settings' \
            python-multipart httpx tenacity greenlet
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入：
#   PINECONE_API_KEY
#   PINECONE_HOST
#   MINIMAX_API_KEY
#   MINIMAX_MODEL=MiniMax-M3
#   JWT_SECRET=<一段随机字符串>
```

### 3. 数据预处理（首次或数据更新时）

按顺序运行：

```bash
python scripts/00a_pdf_to_images.py     # 5 分钟
python scripts/00b_ocr_with_minimax.py  # 10-20 分钟（仅扫描版）
python scripts/00c_verify_ocr.py        # 必做
python scripts/02_chunk_text.py         # 1 分钟
python scripts/03_embed_and_upload.py   # 2-3 分钟
python scripts/04_verify_pinecone.py    # 必做
python scripts/extract_vocab.py         # 提取词表
```

### 4. 启动后端

```bash
uvicorn backend.main:app --port 8000
```

启动时加载 embedding model（首次约 10-15 秒）并自动创建 SQLite 表。

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000)，首次访问跳转到登录页。

### 6. 注册第一个用户

在登录页选择"注册"标签，输入用户名（≥3 字符）和密码（≥4 字符），注册成功自动登录并跳转到主页。

---

## 用户与认证

| 端点 | 方法 | 是否需登录 | 说明 |
|------|------|----------|------|
| `/api/auth/register` | POST | ❌ | 注册（返回 token） |
| `/api/auth/login` | POST | ❌ | 登录（返回 token） |
| `/api/auth/me` | GET | ✅ | 获取当前用户信息 |
| `/api/chat/sync` | POST | ✅ | 同步对话（自动持久化） |
| `/api/chat/stream` | POST | ✅ | 流式对话（自动持久化） |
| `/api/history/sessions` | GET | ✅ | 列出会话 |
| `/api/history/sessions` | POST | ✅ | 新建会话 |
| `/api/history/sessions/{id}` | GET | ✅ | 读取会话及消息 |
| `/api/history/sessions/{id}` | DELETE | ✅ | 删除会话 |
| `/api/quiz/generate` | POST | ❌ | 出题 |
| `/api/quiz/grade` | POST | ✅ | 批改（自动保存进度） |
| `/api/vocab/*` | GET | ❌ | 词汇查询（公开） |
| `/api/progress/*` | GET/POST | ✅ | 进度（按用户隔离） |
| `/api/health` | GET | ❌ | 健康检查 |

Token 默认有效期 30 天，存于浏览器 `localStorage`，所有受保护接口通过 `Authorization: Bearer <token>` 头传递。

---

## 关键技术决策

| 决策 | 原因 |
|------|------|
| 用 MiniMax M3 而非 Claude | 项目用户已有 Token Plan 配额，可节省成本；OpenAI 兼容接口，迁移成本低 |
| 文档用 E5 多语言模型 + `passage:/query:` 前缀 | 准确率比不加前缀高 10-15%（AGENTS.md 强制规范） |
| 单选/填空/翻译题统一用 LLM 生成 | 题型一致性高，prompt 简单 |
| SQLite + JWT | 单机部署足够，零配置 |
| 前端用 SSE（而非 WebSocket） | 简单、流式方向单向（仅服务端推流），EventSource 自动重连 |
| OCR 用 MiniMax M3 而非 PaddleOCR | macOS Ventura + M1 上 PaddleOCR 进程卡死（官方未修复），AGENTS.md 禁用 |

---

## 配置项（.env）

| 变量 | 必填 | 说明 |
|------|------|------|
| `PINECONE_API_KEY` | ✅ | Pinecone API Key |
| `PINECONE_HOST` | ✅ | Index 完整 Host（直连用） |
| `PINECONE_INDEX_NAME` | ✅ | `xsjkndb01` |
| `MINIMAX_API_KEY` | ✅ | MiniMax Token Plan Key |
| `MINIMAX_MODEL` | ✅ | `MiniMax-M3` |
| `EMBEDDING_MODEL` | ✅ | `intfloat/multilingual-e5-large` |
| `EMBEDDING_DIMENSION` | ✅ | `1024` |
| `DATABASE_URL` | ❌ | 默认 `sqlite+aiosqlite:///./database/app.db` |
| `MAX_CONTEXT_CHUNKS` | ❌ | 默认 5 |
| `JWT_SECRET` | ✅ | 用于签发/验证 JWT |
| `HTTPS_PROXY` | ❌ | 国内网络代理 |
| `HF_ENDPOINT` | ❌ | HuggingFace 镜像，国内推荐 `https://hf-mirror.com` |

完整模板见 `.env.example`。

---

## 开发规范

所有开发必须遵守 [AGENTS.md](./AGENTS.md) 的规则，关键点：

- 🚫 **禁用 PaddleOCR**（macOS 13 Ventura + M1 卡死）
- ✅ **E5 模型必须加前缀**（文档 `passage:`、查询 `query:`）
- ✅ **Pinecone 优先 Host 直连**（不是只用 index 名）
- ✅ **分步开发**（每步完成后验证，不跳步）
- ✅ **敏感信息从 .env 读取**，不硬编码
- ✅ **错误处理用 @retry 装饰器**

---

## 开发阶段

按规范分 6 个阶段推进，每阶段都有明确的交付物：

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 环境核查 + 数据处理流水线 | ✅ |
| Phase 1 | 后端核心（RAG + 对话） | ✅ |
| Phase 2 | 出题/批改模块 | ✅ |
| Phase 3 | 前端聊天界面 | ✅ |
| Phase 4 | 出题与词汇前端 | ✅ |
| Phase 5 | 学习进度 + 词汇后端 | ✅ |
| Phase 6 | 多用户系统 | ✅ |
| Phase 7 | 对话历史持久化 | ✅ |
| Phase 7+ | 对话模式标签（每条消息记 mode，UI 展示） | ✅ |

详细开发记录见 [docs/初中英语AI学习Agent开发文档.md](./docs/初中英语AI学习Agent开发文档.md) §15-§23（含 Bug Fix 集锦）。

---

## 已知限制

- OCR 阶段 Unit 125 误识别（页码 125 被识别为单元号），影响部分词条归类
- 词汇闪卡缺少间隔重复算法（SM-2 / FSRS），仅支持"认识/不认识"两态
- 前端未做移动端响应式优化
- 未做 Docker 部署 / Railway / Vercel 发布
- 出题成功率 ~80%（quiz JSON 偶发截断，需 UI 重试）
- 完形填空/阅读理解等新题型待加

---

## 产品协作

完整 PM 协作计划见 [docs/PM_PLAN.md](./docs/PM_PLAN.md)。覆盖 4 角色 RACI、7 阶段 PM 动作、3 个核心 Persona、AARRR 海盗指标、用户研究方法、A/B 测试框架、内容运营、增长策略、客服 SLA。

**当前阶段产品状态**：

| 维度 | 状态 | 工具（待搭建） |
|------|------|---------------|
| 需求池 | 0 | Notion |
| PRD | 0 | Notion 模板 |
| 用户访谈 | 0 | Zoom |
| 数据看板 | 0 | PostHog |
| 反馈渠道 | 0 | Intercom |
| 竞品分析 | 0 | Notion 表格 |

**核心 Persona**（详见 PM_PLAN §3.1）：

1. **小张**（主动学习型学生）：13 岁，成绩中上，目标是中考
2. **张妈**（辅导型家长）：35-40 岁，希望看到孩子进步
3. **李老师**（教育者）：英语老师，需要班级管理工具

**北极星指标**：`每周完成测验数 × 平均分`（详见 PM_PLAN §3.3.1）

**AARRR 目标**：
- 7 日激活率 ≥ 40%
- 7 日留存 ≥ 15%
- 30 日留存 ≥ 8%
- NPS ≥ 40

**待办 P1**（上线路径必做）：搭建 Notion、埋 20+ 事件、建 PostHog 看板、3 个 Persona 文档化（详见 [PM_PLAN §8.3](./docs/PM_PLAN.md#83-pm-待办按优先级)）。

**与 3 个配套文档的关系**：
- PM 决策要做什么（PRD）→ 开发看 [AGENTS.md](./AGENTS.md) 实现
- 测试看 [TEST_PLAN.md](./docs/TEST_PLAN.md) 验证
- 运维看 [OPS_PLAN.md](./docs/OPS_PLAN.md) 部署
- PM 看数据驱动下一轮

---

## 运维

完整运维计划见 [docs/OPS_PLAN.md](./docs/OPS_PLAN.md)。覆盖 4 角色协作、7 阶段生命周期、工具栈选择、监控告警、事件响应、备份恢复、成本估算、安全合规、变更发布。

**当前阶段（v3.2）运维状态**：

| 维度 | 状态 | 工具 |
|------|------|------|
| 代码托管 | 待建 | GitHub |
| CI/CD | 待建 | GitHub Actions |
| 生产环境 | 待部署 | Railway + Vercel |
| 监控 | 待配 | Grafana Cloud + Sentry |
| 备份 | 待配 | cron + S3 |
| 域名/HTTPS | 待买 | Namecheap + Cloudflare |

**月度运营成本预估**：~$27（100 DAU 规模，含 M3 订阅 + 主机）

**OnCall 排班** + 5 个 Runbook 见 [OPS_PLAN §5](./docs/OPS_PLAN.md#5-事件响应与-runbook)。

**部署命令**（待配）：

```bash
# 部署到生产
git tag v3.3.0 && git push --tags
# GitHub Action 自动 build + deploy
```

详细 P1-P3 待办见 [OPS_PLAN §10](./docs/OPS_PLAN.md#10-运维待办roadmap)。

---

## 测试

完整测试计划见 [docs/TEST_PLAN.md](./docs/TEST_PLAN.md)。覆盖 7 个维度：

| 维度 | 主要工具 | 何时跑 |
|------|---------|--------|
| 后端功能 | pytest + httpx AsyncClient | 每个 PR |
| 前端功能 | Jest + React Testing Library | 每个 PR |
| 数据流水线 | pytest + 文件系统断言 | 改 00a/00b/02/03 时 |
| 性能 | locust + 监控 | 版本发布前 |
| AI 效果 | 自建评估脚本 + LLM-as-judge | 模型切换/微调前 |
| Harness | GitHub Actions + Playwright | 持续 |
| 风险评估 | 见 TEST_PLAN §10 | 持续 |

**当前状态**：测试框架未搭建（项目早期）。优先级 P1 见 [TEST_PLAN §10.4](./docs/TEST_PLAN.md#104-待办按优先级)。

**手动冒烟测试**（每个 Phase 完成时跑）：
- 后端：`pytest tests/`（待建）
- 前端：`cd frontend && npm run dev`，浏览器走 5 个核心 journey
- 数据：`python scripts/04_verify_pinecone.py`，6/6 通过
- AI 评估：手工抽查 5 条对话 + 5 道题

---

## 路线图（建议）

- 重跑 OCR 修正 Unit 125 误识别（用更智能的章节识别）
- 词汇练习加 SM-2 间隔重复
- Docker Compose 一键部署
- 移动端响应式
- 学习报告导出 PDF

---

## 致谢

- [MiniMax](https://www.minimax.io) — 提供 AI 推理服务
- [Pinecone](https://www.pinecone.io) — 向量数据库
- [Hugging Face](https://huggingface.co) — 开源 embedding 模型
- [Next.js](https://nextjs.org) / [FastAPI](https://fastapi.tiangolo.com) — 应用框架
- [Sentence Transformers](https://www.sbert.net) — 嵌入生成

## 引用本文档

如果这个项目对你的工作有帮助，请引用：

```bibtex
@software{englishmaster2026,
  title = {EnglishMaster Agent: A RAG-based English Learning Assistant for Chinese Middle School Students},
  author = {EnglishMaster Contributors},
  year = {2026},
  url = {https://github.com/xsj/junior-english-agent}
}
```

## 许可

本项目代码按 [MIT License](./LICENSE) 授权。
教材内容版权归人民教育出版社所有，仅用于教育研究目的。
