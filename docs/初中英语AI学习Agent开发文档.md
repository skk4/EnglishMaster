# 初中英语 AI 智能学习 Agent — 完整开发文档

> **目标受众**: Claude Code / 开发工程师  
> **版本**: v2.2（新增 MiniMax M3 Vision OCR 方案，利用已有 Token Plan 配额替代 EasyOCR，质量更好速度更快）  
> **运行环境**: MacBook Pro M1 / 16GB RAM / macOS 13 Ventura  
> **适用教材**: 人教版八年级英语上下册 (Grade 8 PEP)  
> **技术栈**: Python 3.11 · FastAPI · Pinecone · Claude API · Next.js  
> **单一真相源**：本文档是唯一开发参考，无需查阅其他补充文档

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [目录结构](#3-目录结构)
4. [环境依赖与配置](#4-环境依赖与配置)
5. [数据处理流水线](#5-数据处理流水线)（含 OCR 预处理 + 国产模型扩展）
6. [后端 API 服务](#6-后端-api-服务)
7. [Agent 核心逻辑](#7-agent-核心逻辑)
8. [前端界面](#8-前端界面)
9. [Pinecone 向量数据库设计](#9-pinecone-向量数据库设计)
10. [Prompt 工程](#10-prompt-工程)
11. [功能模块详细规格](#11-功能模块详细规格)
12. [API 接口文档](#12-api-接口文档)
13. [部署方案](#13-部署方案)
14. [测试规格](#14-测试规格)
15. [开发顺序与里程碑](#15-开发顺序与里程碑)
16. [Phase 2 — 出题/批改模块](#16-phase-2--出题批改模块)
17. [Phase 3 — 前端聊天界面](#17-phase-3--前端聊天界面)
18. [Phase 4 — 出题与词汇前端](#18-phase-4--出题与词汇前端)
19. [Phase 5 — 学习进度与词汇后端](#19-phase-5--学习进度与词汇后端)
20. [Phase 6 — 多用户系统](#20-phase-6--多用户系统)
21. [Phase 7 — 对话历史持久化](#21-phase-7--对话历史持久化)
22. [Phase 7+ — 对话模式标签](#22-phase-7--对话模式标签)
23. [Bug Fix 集锦](#23-bug-fix-集锦)

---

## 1. 项目概述

### 1.1 项目名称

**EnglishMaster Agent** — 八年级英语 AI 智能学习助手

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 📖 课文问答 | 基于教材内容的 RAG 问答，精确定位到课时和页码 |
| 📝 语法讲解 | 自动识别语法点，结合教材例句解释 |
| 🔤 词汇练习 | 单元词汇记忆、造句、拼写练习 |
| 📋 对话练习 | 模拟英语对话场景，纠错与建议 |
| 🧪 随堂测试 | 自动出题（选择/填空/翻译），即时批改 |
| 📊 学习追踪 | 记录学习进度、薄弱点分析 |

### 1.3 用户画像

- 初中八年级学生（13-14岁）
- 家长辅导场景
- 英语教师备课参考

### 1.4 技术约束与实际环境

**运行硬件**：MacBook Pro M1 / 16GB RAM

**Pinecone Index（已创建，实际配置）**：

| 参数 | 值 |
|------|----|
| Index 名称 | `xsjkndb01` |
| Host | `xsjkndb01-f408jww.svc.aped-4627-b74a...` |
| Cloud / Region | AWS / us-east-1 |
| Type | Dense / On-demand |
| **维度** | **1024** |
| **嵌入模型** | **multilingual-e5-large** |

**PDF 文件情况**：

| 文件 | 大小 | 类型 | 处理方案 |
|------|------|------|---------|
| 教材主文件 | 241.8MB | 扫描版图片 PDF | **EasyOCR**（M1 MPS 加速，免费） |
| 另一份文件 | 10.7MB | 待验证（可能是原生PDF） | `00a` 自动检测：原生则直接提取，扫描则走 EasyOCR |

**OCR 方案**：  
- **方案 B（推荐）**：MiniMax M3 Vision OCR（有 Token Plan 配额，质量更好，约 13万 tokens/册）  
- **方案 A（备选）**：EasyOCR（无需 API，本地免费，M1 MPS 加速）  
> ⚠️ **PaddleOCR 在 macOS 13 Ventura + M1 上进程卡死（GitHub #10839/#13061），官方未修复，全项目禁用**  
**Claude API**：仅后端对话功能使用，OCR 阶段完全不需要  
**虚拟环境**：pyenv + venv（不用 Anaconda，M1 上 Conda 历史包袱多）  
**部署环境**：本地开发优先，可选部署至 Railway/Vercel

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户界面层                           │
│         Next.js 14 (React) + Tailwind CSS               │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                   API 网关层                             │
│              FastAPI (Python 3.11+)                     │
│    /chat  /quiz  /vocabulary  /progress  /upload        │
└───┬──────────────────┬──────────────────────────────────┘
    │                  │
┌───▼──────┐    ┌──────▼──────────────────────────────────┐
│  Agent   │    │              服务层                      │
│  Core    │    │  RAGService │ QuizService │ VocabService │
│(Claude   │    └──────┬───────────────────────────────────┘
│  API)    │           │
└───┬──────┘    ┌──────▼──────────────────────────────────┐
    │           │           数据层                         │
    │           │  Pinecone (向量) │ SQLite (用户/进度)    │
    │           │  PDF原文缓存 (本地文件)                  │
    └───────────┴─────────────────────────────────────────┘
```

### 2.1 数据流说明

**初始化流（一次性，扫描版PDF，M1 本地运行）**:
```
扫描版PDF(241.8MB) → PDF转PNG图片/200DPI(00a,约5min)
                   → [方案A] EasyOCR M1 MPS(00b_easyocr,约20-35min，免费)
                   → [方案B] MiniMax M3 Vision OCR(00b_minimax,约10-20min，推荐★)
                   → OCR质量验证(00c)
                   → TextChunker(02)
                   → multilingual-e5-large嵌入/M1 MPS加速(03,约2-3min)
                   → Pinecone Upsert[xsjkndb01, 1024维]

原生PDF(10.7MB)    → PyMuPDF直接提取文字(00a自动检测，跳过OCR)
                   → TextChunker(02) → ...
```

**查询流（每次对话）**:
```
用户输入 → "query: "+输入 → multilingual-e5-large(1024维) → Pinecone[xsjkndb01](top-k=5)
        → 上下文组装 → Claude API(对话) → 流式响应 → 前端渲染
```

---

## 3. 目录结构

```
english-agent/
├── README.md
├── .env.example                    # 环境变量模板
├── .env                            # 实际环境变量（不提交git）
├── .gitignore
│
├── data/                           # 数据目录
│   ├── raw/                        # 原始PDF文件
│   │   ├── grade8_semester1.pdf    # 八年级上册
│   │   └── grade8_semester2.pdf    # 八年级下册
│   ├── processed/                  # 处理后的JSON文件
│   │   ├── chunks_semester1.json
│   │   └── chunks_semester2.json
│   └── vocab/                      # 词汇表（可选手动维护）
│       ├── semester1_vocab.json
│       └── semester2_vocab.json
│
├── scripts/                        # 数据处理脚本
│   ├── 00a_pdf_to_images.py        # 【扫描版】PDF转PNG + 自动检测原生PDF
│   ├── 00b_ocr_with_easyocr.py     # 【扫描版】EasyOCR + M1 MPS（PaddleOCR在macOS13 M1卡死，禁用）
│   ├── 00c_verify_ocr.py           # 【扫描版】OCR质量验证
│   ├── 02_chunk_text.py            # 文本分块
│   ├── 03_embed_and_upload.py      # 生成嵌入并上传Pinecone
│   ├── 04_verify_pinecone.py       # 验证上传结果
│   └── extract_vocab.py            # 提取词汇表
│
├── backend/                        # FastAPI 后端
│   ├── main.py                     # FastAPI 入口
│   ├── config.py                   # 配置管理
│   ├── dependencies.py             # 依赖注入
│   │
│   ├── routers/                    # API 路由
│   │   ├── __init__.py
│   │   ├── chat.py                 # 对话接口
│   │   ├── quiz.py                 # 测试接口
│   │   ├── vocabulary.py           # 词汇接口
│   │   └── progress.py             # 进度接口
│   │
│   ├── services/                   # 业务逻辑
│   │   ├── __init__.py
│   │   ├── rag_service.py          # RAG检索服务
│   │   ├── agent_service.py        # Agent 核心
│   │   ├── quiz_service.py         # 出题服务
│   │   ├── vocab_service.py        # 词汇服务
│   │   └── progress_service.py     # 进度追踪
│   │
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   ├── request_models.py       # Pydantic 请求模型
│   │   ├── response_models.py      # Pydantic 响应模型
│   │   └── db_models.py            # SQLite 数据模型
│   │
│   ├── prompts/                    # Prompt 模板
│   │   ├── system_prompt.py        # 系统提示词
│   │   ├── grammar_prompt.py       # 语法解释提示词
│   │   ├── quiz_prompt.py          # 出题提示词
│   │   └── conversation_prompt.py  # 对话练习提示词
│   │
│   └── utils/
│       ├── __init__.py
│       ├── embedding.py            # 嵌入工具
│       └── text_utils.py           # 文本处理工具
│
├── frontend/                       # Next.js 前端
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   │
│   ├── app/                        # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx                # 首页（学习仪表板）
│   │   ├── chat/
│   │   │   └── page.tsx            # 聊天页面
│   │   ├── quiz/
│   │   │   └── page.tsx            # 测试页面
│   │   ├── vocabulary/
│   │   │   └── page.tsx            # 词汇页面
│   │   └── progress/
│   │       └── page.tsx            # 进度页面
│   │
│   ├── components/
│   │   ├── ui/                     # 基础UI组件
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Badge.tsx
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx      # 聊天窗口
│   │   │   ├── MessageBubble.tsx   # 消息气泡
│   │   │   └── InputBar.tsx        # 输入栏
│   │   ├── quiz/
│   │   │   ├── QuizCard.tsx        # 题卡
│   │   │   └── ResultPanel.tsx     # 结果面板
│   │   └── vocab/
│   │       ├── FlashCard.tsx       # 单词卡片
│   │       └── WordList.tsx        # 词汇列表
│   │
│   ├── hooks/
│   │   ├── useChat.ts              # 聊天逻辑
│   │   ├── useQuiz.ts              # 测试逻辑
│   │   └── useProgress.ts          # 进度逻辑
│   │
│   ├── lib/
│   │   ├── api.ts                  # API 客户端
│   │   └── types.ts                # TypeScript 类型
│   │
│   └── public/
│       └── icons/
│
├── database/
│   └── schema.sql                  # SQLite 表结构
│
├── tests/
│   ├── test_rag_service.py
│   ├── test_quiz_service.py
│   └── test_agent_service.py
│
├── docker-compose.yml              # 可选 Docker 部署
├── requirements.txt                # Python 依赖
└── Makefile                        # 快捷命令
```

---

## 4. 环境依赖与配置

### 4.1 Python 依赖 (`requirements.txt`)

```txt
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.12

# AI & Embeddings
anthropic==0.40.0
pinecone==5.0.1
sentence-transformers==3.2.1
torch==2.4.0          # M1 MPS 已内置，pip install torch 直接安装

# OCR（macOS 13 Ventura M1 专用方案）
# ⚠️ PaddleOCR 在 macOS 13 Ventura + M1 上进程卡死（GitHub #10839），全项目禁用
# 使用 EasyOCR 替代（pip install easyocr，基于 PyTorch，M1 MPS 加速）
easyocr==1.7.2

# PDF Processing
pymupdf==1.24.14      # PDF → PNG 图片 / 原生 PDF 直接提取文字

# Database
sqlalchemy==2.0.36
aiosqlite==0.20.0

# Utilities
pydantic==2.9.2
pydantic-settings==2.6.1
python-dotenv==1.0.1
httpx==0.27.2
tenacity==9.0.0

# Dev
pytest==8.3.3
pytest-asyncio==0.24.0
```

### 4.2 环境变量 (`.env.example`)

```bash
# ===== Claude API =====
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# ===== MiniMax API（用于 OCR + 可选对话）=====
# 从 platform.minimax.io 获取，Token Plan 的 sk-cp-xxx 开头
MINIMAX_API_KEY=sk-cp-xxxxxxxxxxxx
MINIMAX_MODEL=MiniMax-M3-highspeed   # 或 MiniMax-M3（结果一致，前者更快）

# ===== Pinecone（已创建 Index，直接填入以下值）=====
PINECONE_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PINECONE_INDEX_NAME=xsjkndb01
PINECONE_HOST=xsjkndb01-f408jww.svc.aped-4627-b74a...   # 从 Pinecone 控制台复制完整 Host
PINECONE_ENVIRONMENT=us-east-1

# ===== Embedding Model（必须与 Pinecone Index 维度匹配）=====
# Index 维度：1024，对应模型：multilingual-e5-large
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIMENSION=1024
# ⚠️ E5 模型查询时需加前缀，代码中已处理，此处仅作说明
# 文档嵌入前缀: "passage: "
# 查询嵌入前缀: "query: "

# ===== Application =====
APP_ENV=development               # development | production
APP_SECRET_KEY=change-this-in-production
DATABASE_URL=sqlite+aiosqlite:///./database/app.db
MAX_CONTEXT_CHUNKS=5             # RAG检索返回的最大片段数
CHUNK_OVERLAP=50                 # 文本分块重叠字符数

# ===== Claude Model =====
# 成本优先: claude-haiku-4-5-20251001
# 质量优先: claude-sonnet-4-6
CLAUDE_MODEL=claude-haiku-4-5-20251001
MAX_TOKENS=2048

# ===== CORS =====
FRONTEND_URL=http://localhost:3000

# ===== 国内网络代理（如需要）=====
# HTTPS_PROXY=http://127.0.0.1:7890
# HF_ENDPOINT=https://hf-mirror.com   # multilingual-e5-large 模型下载加速
```

### 4.3 前端依赖 (`frontend/package.json`)

```json
{
  "name": "english-agent-frontend",
  "version": "0.1.0",
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.6.0",
    "tailwindcss": "^3.4.0",
    "@tailwindcss/typography": "^0.5.15",
    "axios": "^1.7.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "framer-motion": "^11.0.0",
    "zustand": "^5.0.0",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/node": "^22.0.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "^14.2.0"
  }
}
```

---

## 5. 数据处理流水线

> **PDF 类型说明**：本项目有两个 PDF 文件，处理方式不同：
> - `241.8MB`：扫描版图片 PDF → 需要走完整 OCR 流水线（Step 0a → 0b → 0c）
> - `10.7MB`：待检测，`00a` 脚本会自动识别——若是原生 PDF 直接提取文字，跳过 OCR

### 5.0 OCR 预处理（扫描版专用）

#### OCR 方案选型（macOS 13 Ventura + M1）

| 方案 | 费用 | 中英混排 | macOS 13 M1 | 速度 | 结论 |
|------|------|---------|-------------|------|------|
| **EasyOCR**（方案 A，默认） | 完全免费 | ⭐⭐⭐⭐ | ✅ 完全正常 | 20-35分钟/册 | 🥇 无API首选 |
| **MiniMax M3 Vision**（方案 B） | 消耗订阅配额 | ⭐⭐⭐⭐⭐ | ✅ 云端调用 | 10-20分钟/册 | 🥈 **有配额时升级** |
| PaddleOCR | 免费 | ⭐⭐⭐⭐ | ❌ 卡死bug | — | 🚫 **全项目禁用** |
| Claude Vision OCR | 需单独付费 | ⭐⭐⭐⭐⭐ | ✅ | 15-20分钟 | 备选 |
| 百度OCR API | 免费额度 | ⭐⭐⭐⭐⭐ | ✅ | 快 | 备选 |

> ⚠️ **PaddleOCR 在 macOS Ventura M1 上进程卡死（GitHub #10839/#13061），官方未修复，全项目禁用。**

**你当前的情况**：有 MiniMax Token Plan（~0.5B tokens/月），直接用方案 B。  
图片每页约消耗 500-1500 tokens，130 页约 **15-20万 tokens**，占月配额不到 0.1%，完全够用。

#### 方案对比与选择

```
有 MiniMax Token Plan（当前情况）
  → 用方案 B（MiniMax M3 Vision OCR）
  → 质量更好，速度更快，配额足够
  → 脚本：scripts/00b_ocr_with_minimax.py

没有任何 API 配额
  → 用方案 A（EasyOCR）
  → 完全免费，本地运行，速度略慢
  → 脚本：scripts/00b_ocr_with_easyocr.py

后续有 Claude API
  → 两者质量相当，继续用 MiniMax 节省 Claude 配额
```

#### M1 全流程时间预估

| 阶段 | 方案 A (EasyOCR) | 方案 B (MiniMax M3) |
|------|----------------|-------------------|
| PDF → PNG 图片（241.8MB） | 约 3-5 分钟 | 约 3-5 分钟 |
| OCR 处理（约130页） | 约 20-35 分钟 | 约 10-20 分钟 |
| OCR 质量验证 | 约 5 分钟 | 约 5 分钟 |
| 文本分块 + Embedding + Pinecone | 约 3-4 分钟 | 约 3-4 分钟 |
| **全流程合计** | **约 35-50 分钟** | **约 20-35 分钟** |

#### 安装依赖

```bash
# 方案 A 额外安装（方案 B 不需要）
pip install easyocr    # 约 2GB，含 torch

# 两方案都需要
pip install pymupdf openai python-dotenv   # openai SDK 用于调 MiniMax 兼容接口

# 验证（方案 A）
python3 -c "import easyocr,torch; print('MPS:', torch.backends.mps.is_available())"

# 验证（方案 B）
python3 -c "
import os; from openai import OpenAI
client = OpenAI(api_key=os.getenv('MINIMAX_API_KEY'), base_url='https://api.minimax.io/v1')
print('MiniMax client: OK')
"
```

#### Step 0a：PDF 转图片 (`scripts/00a_pdf_to_images.py`)

```python
"""
功能：将扫描版 PDF 每页转为 PNG 图片；自动检测原生 PDF 直接提取文字
环境：macOS 13 Ventura，M1，pymupdf

DPI 选择：200（推荐），300（高质量，文件约3倍大）
输出：data/images/semester<n>/page_<num>.png
      data/images/semester<n>_manifest.json
"""
import fitz
import json
import re
from pathlib import Path

PDF_FILES = {
    1: "data/raw/grade8_semester1.pdf",   # 241.8MB 扫描版
    2: "data/raw/grade8_semester2.pdf",   # 10.7MB（自动检测类型）
}
DPI = 200


def check_is_native_pdf(pdf_path: str) -> bool:
    doc = fitz.open(pdf_path)
    sample_pages = [4, 9, 14]
    total_chars = sum(
        len(doc[p].get_text("text").strip())
        for p in sample_pages if p < len(doc)
    )
    doc.close()
    return (total_chars // len(sample_pages)) > 100


def extract_native_pdf(pdf_path: str, semester: int) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    current_unit = "Unit 1"
    print(f"  Extracting text directly from native PDF...")
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text").strip()
        if len(text) < 30:
            continue
        unit_match = re.search(r'Unit\s+(\d+)', text, re.IGNORECASE)
        if unit_match:
            current_unit = f"Unit {unit_match.group(1)}"
        section = "General"
        for pattern, name in [
            (r'Section\s+A', "Section A"), (r'Section\s+B', "Section B"),
            (r'Grammar\s+Focus', "Grammar Focus"), (r'Self\s+Check', "Self Check"),
        ]:
            if re.search(pattern, text, re.IGNORECASE):
                section = name
                break
        pages.append({
            "page_num": page_num + 1, "text": text, "unit": current_unit,
            "section": section, "semester": semester,
            "ocr_method": "native_pymupdf", "char_count": len(text)
        })
    doc.close()
    return pages


def pdf_to_images(semester: int) -> list[str]:
    pdf_path = PDF_FILES[semester]
    if not Path(pdf_path).exists():
        print(f"  ⚠️  File not found: {pdf_path}")
        return []

    size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
    print(f"  File: {pdf_path} ({size_mb:.1f} MB)")
    print(f"  Detecting PDF type...")

    if check_is_native_pdf(pdf_path):
        print(f"  ✅ Native PDF — extracting text directly (no OCR needed)")
        pages = extract_native_pdf(pdf_path, semester)
        if pages:
            Path("data/processed").mkdir(parents=True, exist_ok=True)
            output_path = f"data/processed/raw_pages_semester{semester}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(pages, f, ensure_ascii=False, indent=2)
            print(f"  ✅ Saved {len(pages)} pages → {output_path}")
            print(f"  ⏭️  Skip OCR — proceed directly to 02_chunk_text.py")
        return []

    print(f"  📷 Scanned PDF — converting to images at {DPI} DPI...")
    output_dir = Path(f"data/images/semester{semester}")
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    image_paths = []
    matrix = fitz.Matrix(DPI / 72, DPI / 72)

    for page_num in range(total_pages):
        pixmap = doc[page_num].get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        output_path = output_dir / f"page_{page_num + 1:03d}.png"
        pixmap.save(str(output_path))
        image_paths.append(str(output_path))
        if (page_num + 1) % 20 == 0:
            print(f"    {page_num + 1}/{total_pages} pages converted")
    doc.close()

    manifest_path = f"data/images/semester{semester}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({"semester": semester, "total_pages": total_pages,
                   "dpi": DPI, "image_paths": image_paths, "needs_ocr": True}, f, indent=2)

    size_out = sum(Path(p).stat().st_size for p in image_paths) / (1024 * 1024)
    print(f"  ✅ {total_pages} pages → {output_dir}/ ({size_out:.0f} MB)")
    return image_paths


def main():
    print("=== Step 0a: PDF → Images ===\n")
    Path("data/images").mkdir(parents=True, exist_ok=True)
    for semester in [1, 2]:
        print(f"\n--- Semester {semester} ---")
        if not Path(PDF_FILES[semester]).exists():
            print(f"  Not found, skipping.")
            continue
        pdf_to_images(semester)
    print("\n✅ Done.")
    print("   If images generated → run: python scripts/00b_ocr_with_easyocr.py")
    print("   If native PDF detected → skip to: python scripts/02_chunk_text.py")

if __name__ == "__main__":
    main()
```

#### Step 0b：EasyOCR M1 MPS (`scripts/00b_ocr_with_easyocr.py`)

```python
"""
功能：EasyOCR 对教材扫描图片进行 OCR
环境：macOS 13 Ventura，M1 16GB，PyTorch MPS 加速
特点：断点续传（缓存到 data/ocr_cache/），中断后重跑自动跳过已处理页
输出：data/processed/raw_pages_semester<n>.json
"""
import json, re, time
from pathlib import Path
import torch


def init_reader():
    import easyocr
    use_gpu = torch.backends.mps.is_available()
    print(f"Initializing EasyOCR (MPS={use_gpu})...")
    print(f"首次运行会下载模型约 500MB，请耐心等待...")
    reader = easyocr.Reader(
        ['ch_sim', 'en'], gpu=use_gpu,
        model_storage_directory=str(Path.home() / '.EasyOCR' / 'model'),
        verbose=False
    )
    print("✅ EasyOCR ready")
    return reader


def ocr_single_page(reader, image_path: str) -> str:
    results = reader.readtext(image_path, detail=1)
    if not results:
        return ""
    lines = []
    for bbox, text, confidence in results:
        if confidence < 0.5:
            continue
        y_top = min(pt[1] for pt in bbox)
        x_left = min(pt[0] for pt in bbox)
        lines.append((y_top, x_left, text.strip()))
    lines.sort(key=lambda item: (round(item[0] / 20) * 20, item[1]))

    merged, cur_y, cur_texts = [], None, []
    for y, x, text in lines:
        row_y = round(y / 20) * 20
        if cur_y is None or row_y != cur_y:
            if cur_texts:
                merged.append(" ".join(cur_texts))
            cur_y, cur_texts = row_y, [text]
        else:
            cur_texts.append(text)
    if cur_texts:
        merged.append(" ".join(cur_texts))
    return "\n".join(merged)


def detect_unit(text: str, current_unit: str) -> str:
    cn_map = {'一':'1','二':'2','三':'3','四':'4','五':'5',
              '六':'6','七':'7','八':'8','九':'9','十':'10'}
    for pattern in [r'Unit\s+(\d+)', r'UNIT\s+(\d+)', r'第\s*([一二三四五六七八九十\d]+)\s*单元']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return f"Unit {cn_map.get(m.group(1), m.group(1))}"
    return current_unit


def detect_section(text: str) -> str:
    for pattern, name in [
        (r'Section\s+A', "Section A"), (r'Section\s+B', "Section B"),
        (r'Grammar\s+Focus', "Grammar Focus"), (r'Self\s+Check', "Self Check"),
        (r'Vocabulary|词汇', "Vocabulary"),
    ]:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return "General"


def process_semester(reader, semester: int) -> list[dict]:
    manifest_path = f"data/images/semester{semester}_manifest.json"
    if not Path(manifest_path).exists():
        print(f"  ❌ No manifest — run 00a first.")
        return []

    with open(manifest_path) as f:
        manifest = json.load(f)

    image_paths = manifest["image_paths"]
    total = len(image_paths)
    cache_dir = Path(f"data/ocr_cache/semester{semester}")
    cache_dir.mkdir(parents=True, exist_ok=True)

    pages, current_unit, cached, processed, errors = [], "Unit 1", 0, 0, 0
    print(f"\n=== EasyOCR: Semester {semester} ({total} pages) ===")
    start = time.time()

    for idx, image_path in enumerate(image_paths):
        page_num = idx + 1
        cache_file = cache_dir / f"page_{page_num:03d}.json"

        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                cached_data = json.load(f)
            pages.append(cached_data)
            current_unit = cached_data.get("unit", current_unit)
            cached += 1
            continue

        eta = ""
        if processed > 0:
            avg = (time.time() - start) / processed
            eta = f"ETA ~{avg * (total - idx) / 60:.1f}min"
        print(f"  [{page_num:3d}/{total}] OCR... {eta}")

        try:
            text = ocr_single_page(reader, image_path)
            if len(re.sub(r'\s+', '', text)) < 25:
                processed += 1
                continue
            current_unit = detect_unit(text, current_unit)
            section = detect_section(text)
            page_data = {
                "page_num": page_num, "text": text, "unit": current_unit,
                "section": section, "semester": semester,
                "ocr_method": "easyocr_mps", "char_count": len(text)
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)
            pages.append(page_data)
            print(f"    → {current_unit} | {section} | {len(text)} chars")
            processed += 1
        except Exception as e:
            print(f"    ❌ Error: {e}")
            errors += 1
            processed += 1

    print(f"\n✅ Semester {semester}: {(time.time()-start)/60:.1f}min | "
          f"processed={processed} cached={cached} errors={errors}")
    return pages


def save_results(pages: list[dict], semester: int):
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    output_path = f"data/processed/raw_pages_semester{semester}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"💾 {len(pages)} pages → {output_path}")
    unit_counts: dict[str, int] = {}
    for p in pages:
        u = p.get("unit", "Unknown")
        unit_counts[u] = unit_counts.get(u, 0) + 1
    for u in sorted(unit_counts):
        print(f"  {u}: {unit_counts[u]} pages")


def main():
    print("=== Step 0b: EasyOCR (macOS 13 Ventura / M1 MPS) ===\n")
    reader = init_reader()
    for semester in [1, 2]:
        manifest = f"data/images/semester{semester}_manifest.json"
        processed = f"data/processed/raw_pages_semester{semester}.json"
        if Path(processed).exists() and not Path(manifest).exists():
            print(f"\nSemester {semester}: Already processed (native PDF), skipping.")
            continue
        if not Path(manifest).exists():
            print(f"\nSemester {semester}: No manifest, skipping.")
            continue
        pages = process_semester(reader, semester)
        if pages:
            save_results(pages, semester)
    print("\n🎉 OCR complete! Next: python scripts/00c_verify_ocr.py")

if __name__ == "__main__":
    main()
```

#### Step 0c：OCR 质量验证 (`scripts/00c_verify_ocr.py`)

```python
"""
功能：验证 EasyOCR 输出质量
通过标准：平均字符数 >= 150，英文覆盖率 >= 60%，低质量页 < 20%
"""
import json, random, re
from pathlib import Path


def verify(semester: int, sample_size: int = 8) -> bool:
    path = f"data/processed/raw_pages_semester{semester}.json"
    if not Path(path).exists():
        print(f"❌ Not found: {path}")
        return False

    with open(path, encoding="utf-8") as f:
        pages = json.load(f)

    print(f"\n=== OCR Quality Check: Semester {semester} ===")
    print(f"Total pages: {len(pages)}")

    char_counts = [p.get("char_count", len(p["text"])) for p in pages]
    avg = sum(char_counts) // len(char_counts)
    low_quality = sum(1 for c in char_counts if c < 100)
    print(f"Char count: min={min(char_counts)} max={max(char_counts)} avg={avg}")
    if low_quality:
        pct = 100 * low_quality // len(char_counts)
        print(f"{'⚠️ ' if pct > 20 else '✅'} Pages < 100 chars: {low_quality} ({pct}%)")

    unit_counts: dict[str, int] = {}
    for p in pages:
        u = p.get("unit", "Unknown")
        unit_counts[u] = unit_counts.get(u, 0) + 1
    print("Unit distribution:", {u: unit_counts[u] for u in sorted(unit_counts)})

    has_en = sum(1 for p in pages if re.search(r'[A-Za-z]{3,}', p["text"]))
    en_pct = 100 * has_en // len(pages)
    print(f"Pages with English: {has_en}/{len(pages)} ({en_pct}%)")

    print(f"\n=== Random Sample ({sample_size} pages) ===")
    for p in sorted(random.sample(pages, min(sample_size, len(pages))), key=lambda x: x["page_num"]):
        preview = p["text"][:180].replace("\n", " | ")
        print(f"\n  [Page {p['page_num']:3d}] {p['unit']} / {p['section']}")
        print(f"  {preview}")

    issues = []
    if avg < 150:
        issues.append(f"Avg chars too low ({avg}) — try DPI=300 in 00a")
    if en_pct < 60:
        issues.append(f"English coverage low ({en_pct}%) — check images")
    if low_quality > len(pages) * 0.2:
        issues.append(f"Too many low-quality pages ({low_quality})")

    if not issues:
        print("\n✅ Quality PASSED — run: python scripts/02_chunk_text.py")
        return True
    print("\n⚠️  Issues found:")
    for issue in issues:
        print(f"   - {issue}")
    return False


def main():
    all_ok, found = True, False
    for semester in [1, 2]:
        if Path(f"data/processed/raw_pages_semester{semester}.json").exists():
            found = True
            all_ok = verify(semester) and all_ok
    if not found:
        print("❌ No processed files. Run 00a and 00b first.")
        return
    print()
    if all_ok:
        print("🎉 All checks passed! Next: python scripts/02_chunk_text.py")
    else:
        print("🔧 Fix issues above, or proceed if quality is acceptable.")

if __name__ == "__main__":
    main()
```

---

#### Step 0b-B：MiniMax M3 Vision OCR（方案 B，推荐）(`scripts/00b_ocr_with_minimax.py`)

```python
"""
功能：使用 MiniMax M3 Vision API 对教材扫描图片进行 OCR
适用：有 MiniMax Token Plan 配额（~0.5B tokens/月）

优势 vs EasyOCR：
  - 更好的中英混排识别（理解排版语义，非单纯文字识别）
  - 识别对话泡泡、表格、音标等特殊格式
  - 速度更快（约 10-20 分钟/册）
  - 无需本地 GPU，云端处理

Token 消耗估算：
  - 每页图片约 500-1500 tokens（取决于清晰度和内容密度）
  - 130 页 × 平均 1000 tokens ≈ 13万 tokens/册
  - 两册合计约 26万 tokens，占月配额 0.05%，完全够用

API 说明：
  - endpoint: https://api.minimax.io/v1/chat/completions
  - model: MiniMax-M3（或 MiniMax-M3-highspeed，结果完全一致，后者更快）
  - 兼容 OpenAI SDK，设置 base_url 即可
  - 图片传 base64，最大 10MB/张（200DPI 的单页 PNG 约 1-3MB，完全满足）
  - 断点续传：已处理页面缓存到 data/ocr_cache/，中断可续

.env 新增配置：
  MINIMAX_API_KEY=your-sk-cp-xxxx    # 从 platform.minimax.io 获取
  MINIMAX_MODEL=MiniMax-M3-highspeed  # 或 MiniMax-M3

输出：data/processed/raw_pages_semester<n>.json（与 EasyOCR 方案格式完全一致）
"""
import base64
import json
import re
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_MODEL   = os.getenv("MINIMAX_MODEL", "MiniMax-M3-highspeed")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"

OCR_SYSTEM_PROMPT = """你是专业的英语教材 OCR 助手，专门处理人教版初中英语教材（Go for it! Grade 8）的扫描图片。

提取规则：
1. 提取图片中所有可见文字，包括正文、对话、词汇表、练习题、语法说明
2. 识别并标注结构：[UNIT N] [SECTION A/B] [GRAMMAR FOCUS] [VOCABULARY] [SELF CHECK]
3. 对话格式：A: ... / B: ...（保留说话人标识）
4. 词汇表：每词一行，格式 word /phonetic/ 中文释义
5. 填空题用 ___ 表示空格
6. 模糊处用 [不清晰] 标注
7. 直接输出提取的文字，不要添加解释或说明"""

OCR_USER_PROMPT = """提取这张人教版八年级英语教材扫描页中的所有文字。
识别并标注单元和章节结构，保持对话、词汇表、练习题的原有格式。"""


def encode_image(image_path: str) -> str:
    """将图片文件编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def init_client() -> OpenAI:
    if not MINIMAX_API_KEY:
        raise ValueError(
            "MINIMAX_API_KEY 未设置！\n"
            "请在 .env 中添加：MINIMAX_API_KEY=your-sk-cp-xxxx\n"
            "API Key 从 platform.minimax.io 获取"
        )
    client = OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)
    print(f"✅ MiniMax client ready (model: {MINIMAX_MODEL})")
    return client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=20),
    retry=retry_if_exception_type(Exception)
)
def ocr_single_page(client: OpenAI, image_path: str) -> str:
    """
    用 MiniMax M3 Vision 识别单张图片
    图片通过 base64 传入，最大 10MB
    """
    image_data = encode_image(image_path)
    file_size_mb = Path(image_path).stat().st_size / (1024 * 1024)

    if file_size_mb > 9.5:
        # 接近上限时压缩（200DPI 单页通常 1-3MB，一般不会触发）
        print(f"    ⚠️  Image {file_size_mb:.1f}MB near limit, consider reducing DPI")

    response = client.chat.completions.create(
        model=MINIMAX_MODEL,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": OCR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                            "detail": "high"   # 高精度模式，更好识别细小文字
                        }
                    },
                    {"type": "text", "text": OCR_USER_PROMPT}
                ]
            }
        ]
    )

    return response.choices[0].message.content.strip()


def detect_unit(text: str, current_unit: str) -> str:
    cn_map = {'一':'1','二':'2','三':'3','四':'4','五':'5',
              '六':'6','七':'7','八':'8','九':'9','十':'10'}
    for pattern in [r'\[UNIT\s+(\d+)\]', r'Unit\s+(\d+)', r'UNIT\s+(\d+)']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return f"Unit {cn_map.get(m.group(1), m.group(1))}"
    return current_unit


def detect_section(text: str) -> str:
    for pattern, name in [
        (r'\[SECTION\s+A\]|Section\s+A', "Section A"),
        (r'\[SECTION\s+B\]|Section\s+B', "Section B"),
        (r'\[GRAMMAR\s+FOCUS\]|Grammar\s+Focus', "Grammar Focus"),
        (r'\[VOCABULARY\]|Vocabulary', "Vocabulary"),
        (r'\[SELF\s+CHECK\]|Self\s+Check', "Self Check"),
    ]:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return "General"


def process_semester(client: OpenAI, semester: int) -> list[dict]:
    manifest_path = f"data/images/semester{semester}_manifest.json"
    if not Path(manifest_path).exists():
        print(f"  ❌ No manifest — run 00a_pdf_to_images.py first")
        return []

    with open(manifest_path) as f:
        manifest = json.load(f)

    image_paths = manifest["image_paths"]
    total = len(image_paths)
    cache_dir = Path(f"data/ocr_cache/semester{semester}")
    cache_dir.mkdir(parents=True, exist_ok=True)

    pages, current_unit = [], "Unit 1"
    cached, processed, errors = 0, 0, 0
    start = time.time()

    print(f"\n=== MiniMax M3 OCR: Semester {semester} ({total} pages) ===")

    for idx, image_path in enumerate(image_paths):
        page_num = idx + 1
        cache_file = cache_dir / f"page_{page_num:03d}.json"

        # 断点续传
        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
            pages.append(data)
            current_unit = data.get("unit", current_unit)
            cached += 1
            continue

        eta = ""
        if processed > 0:
            avg = (time.time() - start) / processed
            eta = f"ETA ~{avg * (total - idx) / 60:.1f}min"
        print(f"  [{page_num:3d}/{total}] MiniMax OCR... {eta}")

        try:
            text = ocr_single_page(client, image_path)

            if len(re.sub(r'\s+', '', text)) < 25:
                processed += 1
                time.sleep(0.3)
                continue

            current_unit = detect_unit(text, current_unit)
            section = detect_section(text)

            page_data = {
                "page_num": page_num, "text": text,
                "unit": current_unit, "section": section,
                "semester": semester, "ocr_method": "minimax_m3",
                "char_count": len(text)
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)

            pages.append(page_data)
            print(f"    → {current_unit} | {section} | {len(text)} chars")
            processed += 1
            time.sleep(0.3)  # 避免限速

        except Exception as e:
            print(f"    ❌ Error on page {page_num}: {e}")
            errors += 1
            processed += 1
            time.sleep(2)

    print(f"\n✅ Semester {semester}: {(time.time()-start)/60:.1f}min | "
          f"processed={processed} cached={cached} errors={errors}")
    return pages


def save_results(pages: list[dict], semester: int):
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    output_path = f"data/processed/raw_pages_semester{semester}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"💾 {len(pages)} pages → {output_path}")
    unit_counts: dict[str, int] = {}
    for p in pages:
        u = p.get("unit", "Unknown")
        unit_counts[u] = unit_counts.get(u, 0) + 1
    for u in sorted(unit_counts):
        print(f"  {u}: {unit_counts[u]} pages")


def main():
    print("=== Step 0b-B: MiniMax M3 Vision OCR ===\n")
    print(f"Model: {MINIMAX_MODEL}")
    print(f"Estimated tokens: ~130,000 per semester (教材 130 页 × 1000 tokens)")
    print(f"Monthly quota impact: < 0.05% of 0.5B token plan\n")

    client = init_client()

    for semester in [1, 2]:
        manifest = f"data/images/semester{semester}_manifest.json"
        processed = f"data/processed/raw_pages_semester{semester}.json"

        if Path(processed).exists() and not Path(manifest).exists():
            print(f"\nSemester {semester}: Already processed (native PDF), skipping.")
            continue
        if not Path(manifest).exists():
            print(f"\nSemester {semester}: No manifest — run 00a first.")
            continue

        pages = process_semester(client, semester)
        if pages:
            save_results(pages, semester)

    print("\n🎉 MiniMax OCR complete! Next: python scripts/00c_verify_ocr.py")


if __name__ == "__main__":
    main()
```

---

```python
"""
功能：将页面文本分割为适合RAG的语义块
策略：按段落+固定大小双重策略，保留元数据
输出：data/processed/chunks_semester<n>.json

分块规则：
- 目标大小：300-500 tokens（约 400-700 中英文字符）
- 最大大小：600 tokens
- 重叠：50字符
- 保留完整句子，不在句子中间切断
"""
import json
import re
from pathlib import Path

MAX_CHUNK_SIZE = 600    # 字符
TARGET_CHUNK_SIZE = 400
OVERLAP_SIZE = 50

def split_into_sentences(text: str) -> list[str]:
    """将文本分割为句子"""
    # 英文句子结尾 + 中文句子结尾
    pattern = r'(?<=[.!?])\s+|(?<=[。！？])'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks(pages: list[dict]) -> list[dict]:
    chunks = []
    chunk_id = 0
    
    for page in pages:
        sentences = split_into_sentences(page["text"])
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > MAX_CHUNK_SIZE and current_chunk:
                # 保存当前块
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "chunk_id": f"s{page['semester']}_p{page['page_num']}_c{chunk_id}",
                    "text": chunk_text,
                    "metadata": {
                        "page_num": page["page_num"],
                        "unit": page["unit"],
                        "section": page["section"],
                        "semester": page["semester"],
                        "char_count": len(chunk_text)
                    }
                })
                chunk_id += 1
                
                # 重叠：保留最后一句话
                if len(current_chunk) > 1:
                    current_chunk = current_chunk[-1:]
                    current_size = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # 保存最后一个块
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "chunk_id": f"s{page['semester']}_p{page['page_num']}_c{chunk_id}",
                "text": chunk_text,
                "metadata": {
                    "page_num": page["page_num"],
                    "unit": page["unit"],
                    "section": page["section"],
                    "semester": page["semester"],
                    "char_count": len(chunk_text)
                }
            })
            chunk_id += 1
    
    return chunks

def main():
    for semester in [1, 2]:
        input_path = f"data/processed/raw_pages_semester{semester}.json"
        if not Path(input_path).exists():
            print(f"File not found: {input_path}, skipping...")
            continue
        
        with open(input_path, "r", encoding="utf-8") as f:
            pages = json.load(f)
        
        chunks = create_chunks(pages)
        
        output_path = f"data/processed/chunks_semester{semester}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print(f"Semester {semester}: {len(pages)} pages → {len(chunks)} chunks")
        
        # 统计信息
        sizes = [c["metadata"]["char_count"] for c in chunks]
        print(f"  Chunk sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}")

if __name__ == "__main__":
    main()
```

### 5.2 生成嵌入并上传Pinecone (`scripts/03_embed_and_upload.py`)

```python
"""
功能：生成文本嵌入向量，批量上传到 Pinecone index: xsjkndb01
模型：intfloat/multilingual-e5-large（维度 1024，需与 Index 匹配）

⚠️ E5 模型规范：上传文档时文本必须加 "passage: " 前缀

上传策略：
- 批次大小：100条/批
- 每批间隔：0.5秒
- 失败重试：最多3次

注意：Index 已存在，脚本直接连接，不会重新创建
"""
import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

BATCH_SIZE = 100
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "xsjkndb01")
PINECONE_HOST = os.getenv("PINECONE_HOST", "")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

def init_pinecone():
    """连接已有 Pinecone Index（Index 已创建，无需新建）"""
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # 优先使用 Host 直连（更快），否则通过 Index 名连接
    if PINECONE_HOST:
        index = pc.Index(host=PINECONE_HOST)
    else:
        index = pc.Index(INDEX_NAME)
    
    stats = index.describe_index_stats()
    print(f"✅ Connected to index '{INDEX_NAME}'")
    print(f"   Dimension: {stats.dimension} | Current vectors: {stats.total_vector_count}")
    
    # 维度校验
    if stats.dimension != EMBEDDING_DIM:
        raise ValueError(
            f"Dimension mismatch! Index={stats.dimension}, Model={EMBEDDING_DIM}. "
            f"确认 EMBEDDING_DIMENSION={stats.dimension} in .env"
        )
    
    return index

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def upsert_batch(index, vectors: list):
    """带重试的批次上传"""
    index.upsert(vectors=vectors)

def load_all_chunks() -> list[dict]:
    """加载所有分块"""
    all_chunks = []
    for semester in [1, 2]:
        path = f"data/processed/chunks_semester{semester}.json"
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
            all_chunks.extend(chunks)
            print(f"Loaded {len(chunks)} chunks from semester {semester}")
    return all_chunks

def main():
    print("Loading multilingual-e5-large (首次约需下载 2.2GB，请耐心)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # 快速验证维度
    test_vec = model.encode("passage: test")
    assert len(test_vec) == EMBEDDING_DIM, f"Model dimension {len(test_vec)} != {EMBEDDING_DIM}"
    print(f"✅ Model ready, dimension: {len(test_vec)}")
    
    print("Connecting to Pinecone...")
    index = init_pinecone()
    
    chunks = load_all_chunks()
    print(f"Total chunks to upload: {len(chunks)}")
    
    # 分批处理
    total_uploaded = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        
        # ⚠️ E5 规范：文档嵌入必须加 "passage: " 前缀
        texts_with_prefix = [f"passage: {chunk['text']}" for chunk in batch]
        embeddings = model.encode(texts_with_prefix, show_progress_bar=False)
        
        # 构造 Pinecone 向量格式
        vectors = []
        for chunk, embedding in zip(batch, embeddings):
            vectors.append({
                "id": chunk["chunk_id"],
                "values": embedding.tolist(),
                "metadata": {
                    **chunk["metadata"],
                    "text": chunk["text"][:1000]  # Pinecone metadata 大小限制
                }
            })
        
        upsert_batch(index, vectors)
        total_uploaded += len(vectors)
        print(f"Progress: {total_uploaded}/{len(chunks)} ({100*total_uploaded//len(chunks)}%)")
        time.sleep(0.5)
    
    # 最终统计
    time.sleep(2)
    stats = index.describe_index_stats()
    print(f"\n✅ Upload complete!")
    print(f"   Total vectors in '{INDEX_NAME}': {stats.total_vector_count}")

if __name__ == "__main__":
    main()
```

### 5.3 验证检索效果 (`scripts/04_verify_pinecone.py`)

```python
"""
功能：验证 Pinecone 数据完整性，测试 multilingual-e5-large 检索效果
⚠️ 查询时必须加 "query: " 前缀
"""
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

load_dotenv()

def main():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    host = os.getenv("PINECONE_HOST", "")
    if host:
        index = pc.Index(host=host)
    else:
        index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    
    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))
    
    # 1. 基本统计
    stats = index.describe_index_stats()
    print(f"Index: {os.getenv('PINECONE_INDEX_NAME')}")
    print(f"Dimension: {stats.dimension} (expected: 1024)")
    print(f"Total vectors: {stats.total_vector_count}")
    
    # 2. 测试查询（中英文均需能检索到内容）
    test_queries = [
        "What is the past tense of go?",
        "Unit 1 vocabulary words",
        "How to use present perfect tense",
        "第一单元的词汇",
        "过去完成时怎么用",
        "Section A 对话内容",
    ]
    
    print("\n=== Retrieval Test ===")
    for query in test_queries:
        # ⚠️ 必须加 query: 前缀
        query_with_prefix = f"query: {query}"
        embedding = model.encode(query_with_prefix).tolist()
        
        results = index.query(
            vector=embedding,
            top_k=3,
            include_metadata=True
        )
        
        print(f"\nQuery: '{query}'")
        if not results.matches:
            print("  ⚠️ No results found!")
        for match in results.matches:
            print(f"  Score: {match.score:.3f} | {match.metadata.get('unit')} {match.metadata.get('section')} | Page {match.metadata.get('page_num')}")
            print(f"  Text:  {match.metadata.get('text', '')[:80]}...")

if __name__ == "__main__":
    main()
```

---

## 6. 后端 API 服务

### 6.1 配置管理 (`backend/config.py`)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "xsjkndb01"           # 实际 Index 名称
    pinecone_host: str = ""                           # 可选，直连 Host 更快
    pinecone_environment: str = "us-east-1"
    
    # Models
    # ⚠️ 必须与 Pinecone Index 创建时的维度匹配
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dimension: int = 1024                  # multilingual-e5-large 输出维度
    claude_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 2048
    
    # App
    app_env: str = "development"
    app_secret_key: str = "change-me"
    database_url: str = "sqlite+aiosqlite:///./database/app.db"
    max_context_chunks: int = 5
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 6.2 FastAPI 入口 (`backend/main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.config import get_settings
from backend.routers import chat, quiz, vocabulary, progress
from backend.dependencies import startup_services, shutdown_services

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    await startup_services()
    yield
    await shutdown_services()

app = FastAPI(
    title="EnglishMaster Agent API",
    version="1.0.0",
    description="八年级英语 AI 学习助手后端接口",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz"])
app.include_router(vocabulary.router, prefix="/api/vocabulary", tags=["Vocabulary"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "model": settings.claude_model}
```

### 6.3 依赖注入 (`backend/dependencies.py`)

```python
"""
全局单例服务管理
M1 MacBook 专项优化：
  - multilingual-e5-large 使用 MPS 加速（M1 GPU）
  - 首次启动加载模型约 10-15 秒（M1 很快）
"""
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import anthropic
import torch
from backend.config import get_settings

settings = get_settings()

_pinecone_index = None
_embedding_model = None
_anthropic_client = None

async def startup_services():
    global _pinecone_index, _embedding_model, _anthropic_client

    # 检测 M1 MPS 加速
    if torch.backends.mps.is_available():
        device = "mps"
        print(f"Loading embedding model with M1 MPS acceleration...")
    else:
        device = "cpu"
        print(f"Loading embedding model on CPU...")

    _embedding_model = SentenceTransformer(settings.embedding_model, device=device)
    print(f"  ✅ {settings.embedding_model} loaded on {device.upper()}")

    print(f"Connecting to Pinecone index: {settings.pinecone_index_name}")
    pc = Pinecone(api_key=settings.pinecone_api_key)
    if settings.pinecone_host:
        _pinecone_index = pc.Index(host=settings.pinecone_host)
    else:
        _pinecone_index = pc.Index(settings.pinecone_index_name)
    stats = _pinecone_index.describe_index_stats()
    print(f"  ✅ Connected | vectors: {stats.total_vector_count} | dim: {stats.dimension}")

    _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    print("  ✅ Anthropic client ready")
    print("✅ All services initialized")

async def shutdown_services():
    global _pinecone_index, _embedding_model, _anthropic_client
    _pinecone_index = None
    _embedding_model = None
    _anthropic_client = None

def get_pinecone_index():
    return _pinecone_index

def get_embedding_model():
    return _embedding_model

def get_anthropic_client():
    return _anthropic_client
```

---

## 7. Agent 核心逻辑

### 7.1 RAG 检索服务 (`backend/services/rag_service.py`)

```python
"""
RAG检索服务：将用户查询转为向量，从Pinecone检索相关上下文

⚠️ multilingual-e5-large 使用规范：
  - 上传文档时：文本加前缀 "passage: "
  - 查询时：文本加前缀 "query: "
  不加前缀准确率下降约 10-15%
"""
from typing import Optional
from backend.dependencies import get_pinecone_index, get_embedding_model
from backend.config import get_settings

settings = get_settings()

class RAGService:
    def __init__(self):
        self.index = get_pinecone_index()
        self.model = get_embedding_model()
    
    def retrieve(
        self,
        query: str,
        top_k: int = None,
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None
    ) -> list[dict]:
        """
        检索相关内容片段
        
        Args:
            query: 用户查询文本（中文或英文均可，multilingual-e5-large 支持多语言）
            top_k: 返回结果数量
            filter_unit: 过滤特定单元（如 "Unit 3"）
            filter_semester: 过滤学期（1 或 2）
        
        Returns:
            list of {text, score, unit, section, page_num, semester}
        """
        top_k = top_k or settings.max_context_chunks
        
        # ⚠️ E5 模型规范：查询文本必须加 "query: " 前缀
        query_with_prefix = f"query: {query}"
        query_embedding = self.model.encode(query_with_prefix).tolist()
        
        # 维度校验（开发阶段调试用）
        assert len(query_embedding) == 1024, \
            f"Embedding dimension mismatch: expected 1024, got {len(query_embedding)}"
        
        # 构建过滤条件
        filter_dict = {}
        if filter_unit:
            filter_dict["unit"] = {"$eq": filter_unit}
        if filter_semester:
            filter_dict["semester"] = {"$eq": filter_semester}
        
        # Pinecone 查询
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        
        # 格式化结果
        chunks = []
        for match in results.matches:
            if match.score < 0.3:  # 过滤低相关性结果
                continue
            chunks.append({
                "text": match.metadata.get("text", ""),
                "score": match.score,
                "unit": match.metadata.get("unit", ""),
                "section": match.metadata.get("section", ""),
                "page_num": match.metadata.get("page_num", 0),
                "semester": match.metadata.get("semester", 1),
            })
        
        return chunks
    
    def format_context(self, chunks: list[dict]) -> str:
        """将检索结果格式化为Claude可用的上下文字符串"""
        if not chunks:
            return "No relevant textbook content found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = f"{chunk['unit']} {chunk['section']} (Page {chunk['page_num']}, Semester {chunk['semester']})"
            context_parts.append(f"[Source {i}: {source}]\n{chunk['text']}")
        
        return "\n\n---\n\n".join(context_parts)
```

### 7.2 Agent 服务 (`backend/services/agent_service.py`)

```python
"""
Agent核心：管理对话历史，调用Claude API，整合RAG上下文
支持流式输出（Streaming）
"""
import json
from typing import Generator, Optional
from anthropic import Anthropic
from backend.services.rag_service import RAGService
from backend.prompts.system_prompt import build_system_prompt
from backend.config import get_settings
from backend.dependencies import get_anthropic_client

settings = get_settings()

class AgentService:
    def __init__(self):
        self.client: Anthropic = get_anthropic_client()
        self.rag = RAGService()
    
    def chat(
        self,
        user_message: str,
        conversation_history: list[dict],
        mode: str = "general",      # general | grammar | vocabulary | conversation
        unit_filter: Optional[str] = None,
        semester_filter: Optional[int] = None,
        student_level: str = "grade8"
    ) -> Generator[str, None, None]:
        """
        流式对话接口
        
        Args:
            user_message: 用户当前消息
            conversation_history: 历史消息 [{"role": "user"|"assistant", "content": "..."}]
            mode: 对话模式
            unit_filter: 指定单元（可选）
            semester_filter: 指定学期（可选）
            student_level: 学生年级
        
        Yields:
            str: 流式文本片段
        """
        # 1. RAG 检索
        chunks = self.rag.retrieve(
            query=user_message,
            filter_unit=unit_filter,
            filter_semester=semester_filter
        )
        context = self.rag.format_context(chunks)
        
        # 2. 构建系统提示词
        system_prompt = build_system_prompt(
            mode=mode,
            context=context,
            student_level=student_level
        )
        
        # 3. 构建消息历史（保留最近10轮）
        messages = conversation_history[-20:]  # 最近10轮 = 20条消息
        messages.append({"role": "user", "content": user_message})
        
        # 4. 调用 Claude API（流式）
        with self.client.messages.stream(
            model=settings.claude_model,
            max_tokens=settings.max_tokens,
            system=system_prompt,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                yield text
    
    def chat_sync(
        self,
        user_message: str,
        conversation_history: list[dict],
        **kwargs
    ) -> dict:
        """
        同步对话接口（用于测试和出题）
        Returns: {content, usage, sources}
        """
        chunks = self.rag.retrieve(query=user_message, **{
            k: v for k, v in kwargs.items() 
            if k in ["filter_unit", "filter_semester"]
        })
        context = self.rag.format_context(chunks)
        system_prompt = build_system_prompt(
            mode=kwargs.get("mode", "general"),
            context=context,
            student_level=kwargs.get("student_level", "grade8")
        )
        
        messages = conversation_history[-20:]
        messages.append({"role": "user", "content": user_message})
        
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.max_tokens,
            system=system_prompt,
            messages=messages
        )
        
        return {
            "content": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            "sources": [
                {
                    "unit": c["unit"],
                    "section": c["section"],
                    "page_num": c["page_num"],
                    "semester": c["semester"],
                    "score": round(c["score"], 3)
                } for c in chunks
            ]
        }
```

### 7.3 出题服务 (`backend/services/quiz_service.py`)

```python
"""
出题服务：生成各类型英语练习题，支持自动批改
题型：
  - multiple_choice: 单选题（4选1）
  - fill_blank: 填空题
  - translation: 中英互译
  - sentence_reorder: 句子排序
  - grammar_correction: 语法纠错
"""
import json
from backend.services.agent_service import AgentService
from backend.prompts.quiz_prompt import QUIZ_PROMPTS

class QuizService:
    def __init__(self):
        self.agent = AgentService()
    
    def generate_quiz(
        self,
        unit: str,
        semester: int,
        quiz_type: str = "multiple_choice",
        count: int = 5,
        difficulty: str = "medium"  # easy | medium | hard
    ) -> list[dict]:
        """
        生成测试题目
        
        Returns:
            [
              {
                "id": "q1",
                "type": "multiple_choice",
                "question": "...",
                "options": ["A...", "B...", "C...", "D..."],   # 仅选择题
                "answer": "A",                                  # 正确答案
                "explanation": "...",                           # 解析
                "unit": "Unit 1",
                "difficulty": "medium"
              }
            ]
        """
        prompt = QUIZ_PROMPTS[quiz_type].format(
            unit=unit,
            count=count,
            difficulty=difficulty
        )
        
        result = self.agent.chat_sync(
            user_message=prompt,
            conversation_history=[],
            mode="quiz",
            filter_unit=unit,
            filter_semester=semester
        )
        
        # 解析 Claude 返回的 JSON
        try:
            content = result["content"]
            # 提取 JSON 块
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            questions = json.loads(json_str)
            return questions
        except (json.JSONDecodeError, IndexError) as e:
            # 解析失败时返回错误信息
            return [{"error": f"Failed to parse quiz: {str(e)}", "raw": result["content"]}]
    
    def grade_answer(
        self,
        question: dict,
        student_answer: str
    ) -> dict:
        """
        批改学生答案
        Returns: {is_correct, score, feedback, correct_answer}
        """
        quiz_type = question.get("type", "fill_blank")
        
        if quiz_type == "multiple_choice":
            is_correct = student_answer.strip().upper() == question["answer"].strip().upper()
            return {
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "feedback": question.get("explanation", ""),
                "correct_answer": question["answer"]
            }
        
        # 主观题用 Claude 批改
        grade_prompt = f"""
Grade this student answer for a {quiz_type} question.

Question: {question['question']}
Reference Answer: {question['answer']}
Student Answer: {student_answer}

Respond in JSON format:
{{
  "is_correct": true/false,
  "score": 0.0-1.0,
  "feedback": "specific feedback in Chinese, max 2 sentences",
  "correct_answer": "the correct answer"
}}
"""
        result = self.agent.chat_sync(
            user_message=grade_prompt,
            conversation_history=[],
            mode="quiz"
        )
        
        try:
            content = result["content"]
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            return json.loads(json_str)
        except:
            return {
                "is_correct": False,
                "score": 0.0,
                "feedback": result["content"],
                "correct_answer": question.get("answer", "")
            }
```

---

## 8. 前端界面

### 8.1 API 客户端 (`frontend/lib/api.ts`)

```typescript
import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

// ===== Chat API =====
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
  mode?: 'general' | 'grammar' | 'vocabulary' | 'conversation';
  unit_filter?: string;
  semester_filter?: number;
}

export interface ChatSource {
  unit: string;
  section: string;
  page_num: number;
  semester: number;
  score: number;
}

// 流式对话（使用 EventSource）
export function streamChat(
  request: ChatRequest,
  onChunk: (text: string) => void,
  onDone: (sources: ChatSource[]) => void,
  onError: (error: Error) => void
): () => void {
  const controller = new AbortController();
  
  fetch(`${BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal: controller.signal,
  })
  .then(async (response) => {
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') continue;
          
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'text') {
              onChunk(parsed.content);
            } else if (parsed.type === 'done') {
              onDone(parsed.sources || []);
            }
          } catch {}
        }
      }
    }
  })
  .catch(onError);
  
  return () => controller.abort();
}

// ===== Quiz API =====
export interface QuizQuestion {
  id: string;
  type: 'multiple_choice' | 'fill_blank' | 'translation' | 'grammar_correction';
  question: string;
  options?: string[];
  answer: string;
  explanation: string;
  unit: string;
  difficulty: string;
}

export const generateQuiz = (params: {
  unit: string;
  semester: number;
  quiz_type?: string;
  count?: number;
  difficulty?: string;
}) => api.post<QuizQuestion[]>('/api/quiz/generate', params).then(r => r.data);

export const gradeAnswer = (params: {
  question: QuizQuestion;
  student_answer: string;
}) => api.post('/api/quiz/grade', params).then(r => r.data);

// ===== Vocabulary API =====
export const getUnitVocab = (unit: string, semester: number) =>
  api.get(`/api/vocabulary/${semester}/${encodeURIComponent(unit)}`).then(r => r.data);

// ===== Progress API =====
export const getProgress = (userId: string) =>
  api.get(`/api/progress/${userId}`).then(r => r.data);

export const saveProgress = (data: {
  user_id: string;
  unit: string;
  activity_type: string;
  score?: number;
}) => api.post('/api/progress/save', data).then(r => r.data);
```

### 8.2 聊天 Hook (`frontend/hooks/useChat.ts`)

```typescript
import { useState, useCallback, useRef } from 'react';
import { ChatMessage, streamChat, ChatSource } from '@/lib/api';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  
  const sendMessage = useCallback(async (
    content: string,
    options?: {
      mode?: ChatMessage['role'];
      unit_filter?: string;
      semester_filter?: number;
    }
  ) => {
    if (isLoading) return;
    
    const userMessage: ChatMessage = { role: 'user', content };
    const updatedHistory = [...messages, userMessage];
    setMessages(updatedHistory);
    setIsLoading(true);
    setError(null);
    setSources([]);
    
    // 添加空的 assistant 消息（流式填充）
    const assistantMessage: ChatMessage = { role: 'assistant', content: '' };
    setMessages([...updatedHistory, assistantMessage]);
    
    let accumulated = '';
    
    const abort = streamChat(
      {
        message: content,
        history: messages,
        mode: (options?.mode as any) || 'general',
        unit_filter: options?.unit_filter,
        semester_filter: options?.semester_filter,
      },
      (chunk) => {
        accumulated += chunk;
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'assistant', content: accumulated };
          return updated;
        });
      },
      (receivedSources) => {
        setSources(receivedSources);
        setIsLoading(false);
      },
      (err) => {
        setError(err.message);
        setIsLoading(false);
      }
    );
    
    abortRef.current = abort;
  }, [messages, isLoading]);
  
  const clearHistory = useCallback(() => {
    setMessages([]);
    setSources([]);
    setError(null);
  }, []);
  
  const stopGeneration = useCallback(() => {
    abortRef.current?.();
    setIsLoading(false);
  }, []);
  
  return {
    messages,
    isLoading,
    sources,
    error,
    sendMessage,
    clearHistory,
    stopGeneration,
  };
}
```

### 8.3 聊天路由 (`backend/routers/chat.py`)

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from backend.models.request_models import ChatRequest
from backend.services.agent_service import AgentService

router = APIRouter()
agent_service = AgentService()

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """流式对话接口（Server-Sent Events）"""
    
    async def generate():
        sources = []
        
        # 先获取 RAG 结果（同步）
        chunks = agent_service.rag.retrieve(
            query=request.message,
            filter_unit=request.unit_filter,
            filter_semester=request.semester_filter
        )
        sources = [
            {
                "unit": c["unit"],
                "section": c["section"],
                "page_num": c["page_num"],
                "semester": c["semester"],
                "score": round(c["score"], 3)
            } for c in chunks
        ]
        context = agent_service.rag.format_context(chunks)
        
        from backend.prompts.system_prompt import build_system_prompt
        from backend.config import get_settings
        from backend.dependencies import get_anthropic_client
        
        settings = get_settings()
        client = get_anthropic_client()
        system_prompt = build_system_prompt(
            mode=request.mode,
            context=context,
            student_level="grade8"
        )
        
        messages = request.history[-20:]
        messages.append({"role": "user", "content": request.message})
        
        with client.messages.stream(
            model=settings.claude_model,
            max_tokens=settings.max_tokens,
            system=system_prompt,
            messages=[{"role": m.role, "content": m.content} for m in messages]
        ) as stream:
            for text in stream.text_stream:
                data = json.dumps({"type": "text", "content": text})
                yield f"data: {data}\n\n"
        
        # 发送来源信息
        done_data = json.dumps({"type": "done", "sources": sources})
        yield f"data: {done_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/sync")
async def chat_sync(request: ChatRequest):
    """同步对话接口（用于简单查询）"""
    result = agent_service.chat_sync(
        user_message=request.message,
        conversation_history=[{"role": m.role, "content": m.content} for m in request.history],
        mode=request.mode,
        filter_unit=request.unit_filter,
        filter_semester=request.semester_filter
    )
    return result
```

---

## 9. Pinecone 向量数据库设计

### 9.1 实际 Index 配置（已创建，勿重复创建）

```
Index Name:  xsjkndb01
Host:        xsjkndb01-f408jww.svc.aped-4627-b74a...（从控制台复制完整值）
Dimension:   1024        (multilingual-e5-large 输出维度，固定不可更改)
Metric:      cosine      (语义相似度标准选择)
Cloud:       aws
Region:      us-east-1
Type:        Dense
Capacity:    On-demand
```

> ⚠️ **Index 已创建**：`scripts/03_embed_and_upload.py` 中的 `create_index` 逻辑不会被触发（Index 已存在时跳过），直接连接即可。

### 9.2 嵌入模型使用规范（multilingual-e5-large）

E5 系列模型要求区分"文档"和"查询"两种使用场景，必须加对应前缀：

```python
# ✅ 上传文档时（scripts/03_embed_and_upload.py）
texts_with_prefix = [f"passage: {chunk['text']}" for chunk in batch]
embeddings = model.encode(texts_with_prefix)

# ✅ 查询时（backend/services/rag_service.py）
query_with_prefix = f"query: {user_input}"
query_embedding = model.encode(query_with_prefix)

# ❌ 错误：不加前缀，准确率下降 10-15%
embedding = model.encode(text)
```

### 9.3 向量 Metadata 设计

每个向量携带以下 metadata（Pinecone 免费层 metadata 限制 40KB/向量）：

```json
{
  "text": "原始文本（最多1000字符）",
  "page_num": 15,
  "unit": "Unit 3",
  "section": "Section A",
  "semester": 1,
  "char_count": 384
}
```

### 9.3 查询过滤策略

| 场景 | 过滤条件 | Top-K |
|------|---------|-------|
| 全局问答 | 无过滤 | 5 |
| 指定单元 | `unit = "Unit 3"` | 5 |
| 指定学期 | `semester = 1` | 5 |
| 词汇查询 | `unit = X, section = "Vocabulary"` | 3 |
| 语法查询 | `section = "Grammar Focus"` | 5 |

### 9.4 向量数量估算

| 内容 | 页数估算 | 平均分块/页 | 向量数 |
|------|---------|------------|--------|
| 八年级上册 | ~130页 | 2.5 | ~325 |
| 八年级下册 | ~130页 | 2.5 | ~325 |
| **合计** | | | **~650** |

> On-demand 模式无硬性向量上限，650 个向量远低于任何限制，成本几乎为零。
> multilingual-e5-large 每个向量占用 1024 × 4 bytes = 4KB，650 个向量约 **2.6MB** 存储。

### 9.5 国产大模型 Embedding 适配（可选扩展）

需要切换国产模型时（数据不出境、成本优化等），使用统一适配层，切换只改 `.env`，代码无需修改。

#### 国产模型速查（与当前 1024 维 Index 兼容）

| 厂商 | 模型 | 可用维度 | 价格/M tokens | 网络 |
|------|------|---------|-------------|------|
| 阿里云百炼 | `text-embedding-v4` | 自定义→**1024** | ¥0.05 | 国内直连 |
| 智谱AI | `embedding-3` | 自定义→**1024**（默认2048，必须显式设） | ¥0.07 | 国内直连 |
| 火山方舟 | `doubao-embedding` | 自定义→**1024** | 极低 | 国内直连 |
| 百度千帆 | `Embedding-V1` | 固定384 | ❌ 维度不兼容 | — |
| 本地（当前） | `multilingual-e5-large` | 固定**1024** | 免费 | 无需网络 |

#### .env 切换配置

```bash
# 当前默认（本地免费）
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DIMENSION=1024
EMBEDDING_USE_E5_PREFIX=true

# 切换阿里云百炼（取消注释以下行，注释掉上面）
# EMBEDDING_PROVIDER=aliyun
# EMBEDDING_MODEL=text-embedding-v4
# EMBEDDING_DIMENSION=1024
# DASHSCOPE_API_KEY=sk-xxxx
# EMBEDDING_USE_E5_PREFIX=false   # 阿里云内部处理，不需要前缀

# 切换智谱AI
# EMBEDDING_PROVIDER=zhipu
# EMBEDDING_MODEL=embedding-3
# EMBEDDING_DIMENSION=1024        # ⚠️ 智谱默认2048，必须显式设为1024
# ZHIPUAI_API_KEY=xxxx

# 切换火山方舟（豆包）
# EMBEDDING_PROVIDER=volcengine
# EMBEDDING_MODEL=doubao-embedding
# EMBEDDING_DIMENSION=1024
# ARK_API_KEY=xxxx
```

#### 统一适配层 (`backend/utils/embedding.py`)

```python
"""
统一 Embedding 适配层
切换提供商只修改 .env 的 EMBEDDING_PROVIDER，代码无需改动
支持：local | aliyun | zhipu | volcengine
"""
import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
USE_E5_PREFIX = os.getenv("EMBEDDING_USE_E5_PREFIX", "true").lower() == "true"


class BaseEmbedder(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: pass
    @abstractmethod
    def embed_query(self, text: str) -> list[float]: pass
    def validate_dimension(self, vector: list[float]):
        assert len(vector) == DIMENSION, \
            f"维度不匹配！期望 {DIMENSION}，实际 {len(vector)}"


class LocalEmbedder(BaseEmbedder):
    """本地 multilingual-e5-large，M1 MPS 加速，完全免费"""
    def __init__(self):
        import torch
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=device)
        self.use_prefix = USE_E5_PREFIX
        print(f"✅ LocalEmbedder: {model_name} on {device.upper()}")

    def embed_documents(self, texts):
        if self.use_prefix:
            texts = [f"passage: {t}" for t in texts]
        result = [v.tolist() for v in self.model.encode(texts, show_progress_bar=False)]
        self.validate_dimension(result[0])
        return result

    def embed_query(self, text):
        if self.use_prefix:
            text = f"query: {text}"
        vector = self.model.encode(text).tolist()
        self.validate_dimension(vector)
        return vector


class AliyunEmbedder(BaseEmbedder):
    """阿里云百炼 text-embedding-v4，单批最多25条，pip install dashscope"""
    BATCH_SIZE = 25
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
        if not self.api_key: raise ValueError("DASHSCOPE_API_KEY 未设置")
        print(f"✅ AliyunEmbedder: {self.model}, dim={DIMENSION}")

    def _call(self, texts, text_type):
        from dashscope import TextEmbedding
        from http import HTTPStatus
        resp = TextEmbedding.call(api_key=self.api_key, model=self.model,
                                  input=texts, dimension=DIMENSION, text_type=text_type)
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"阿里云 API 错误: {resp.message}")
        return [item["embedding"] for item in resp.output["embeddings"]]

    def embed_documents(self, texts):
        result = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            result.extend(self._call(texts[i:i+self.BATCH_SIZE], "document"))
        self.validate_dimension(result[0])
        return result

    def embed_query(self, text):
        vector = self._call([text], "query")[0]
        self.validate_dimension(vector)
        return vector


class ZhipuEmbedder(BaseEmbedder):
    """智谱 embedding-3，⚠️ 默认2048维，必须设 dimensions=1024，pip install zhipuai"""
    BATCH_SIZE = 64
    def __init__(self):
        from zhipuai import ZhipuAI
        api_key = os.getenv("ZHIPUAI_API_KEY")
        if not api_key: raise ValueError("ZHIPUAI_API_KEY 未设置")
        self.client = ZhipuAI(api_key=api_key)
        self.model = os.getenv("EMBEDDING_MODEL", "embedding-3")
        print(f"✅ ZhipuEmbedder: {self.model}, dim={DIMENSION}")

    def _call(self, texts):
        resp = self.client.embeddings.create(model=self.model, input=texts, dimensions=DIMENSION)
        return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]

    def embed_documents(self, texts):
        result = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            result.extend(self._call(texts[i:i+self.BATCH_SIZE]))
        self.validate_dimension(result[0])
        return result

    def embed_query(self, text):
        vector = self._call([text])[0]
        self.validate_dimension(vector)
        return vector


class VolcengineEmbedder(BaseEmbedder):
    """火山方舟 doubao-embedding，兼容 OpenAI SDK"""
    BATCH_SIZE = 32
    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("ARK_API_KEY")
        if not api_key: raise ValueError("ARK_API_KEY 未设置")
        self.client = OpenAI(api_key=api_key, base_url="https://ark.cn-beijing.volces.com/api/v3")
        self.model = os.getenv("EMBEDDING_MODEL", "doubao-embedding")
        print(f"✅ VolcengineEmbedder: {self.model}, dim={DIMENSION}")

    def _call(self, texts):
        resp = self.client.embeddings.create(model=self.model, input=texts, dimensions=DIMENSION)
        return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]

    def embed_documents(self, texts):
        result = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            result.extend(self._call(texts[i:i+self.BATCH_SIZE]))
        self.validate_dimension(result[0])
        return result

    def embed_query(self, text):
        vector = self._call([text])[0]
        self.validate_dimension(vector)
        return vector


def get_embedder() -> BaseEmbedder:
    """工厂函数：根据 EMBEDDING_PROVIDER 返回对应 Embedder，在 startup_services() 中调用"""
    providers = {"local": LocalEmbedder, "aliyun": AliyunEmbedder,
                 "zhipu": ZhipuEmbedder, "volcengine": VolcengineEmbedder}
    if PROVIDER not in providers:
        raise ValueError(f"不支持的 EMBEDDING_PROVIDER: '{PROVIDER}'，可选: {list(providers)}")
    return providers[PROVIDER]()
```

#### 切换提供商流程

```bash
# 1. 修改 .env（参见上方配置）
# 2. 验证新提供商
python scripts/test_embedding_provider.py

# 3. 切换模型必须清空旧向量重新上传（不同模型向量空间不兼容）
python scripts/05_clear_pinecone.py    # ⚠️ 不可逆，输入 yes 确认
python scripts/03_embed_and_upload.py
python scripts/04_verify_pinecone.py
```

#### 验证脚本 (`scripts/test_embedding_provider.py`)

```python
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from backend.utils.embedding import get_embedder, DIMENSION

def main():
    provider = os.getenv("EMBEDDING_PROVIDER", "local")
    print(f"\n=== Testing: {provider} ===")
    embedder = get_embedder()

    docs = embedder.embed_documents(["Unit 1 vocabulary", "过去进行时", "The cat sat."])
    print(f"✅ embed_documents: {len(docs)} vectors, dim={len(docs[0])}")

    query = embedder.embed_query("过去进行时怎么用？")
    print(f"✅ embed_query: dim={len(query)}")

    assert len(docs[0]) == DIMENSION, f"❌ 维度错误: {len(docs[0])} != {DIMENSION}"
    print(f"✅ Dimension OK: {DIMENSION}")

    v1 = np.array(embedder.embed_query("past continuous tense"))
    v2 = np.array(embedder.embed_query("过去进行时"))
    sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    print(f"✅ Cross-lingual similarity: {sim:.3f} {'(OK)' if sim > 0.5 else '(⚠️ Low)'}")
    print(f"\n🎉 Provider '{provider}' 验证通过！")

if __name__ == "__main__":
    main()
```

#### 清空 Pinecone 脚本 (`scripts/05_clear_pinecone.py`)

```python
"""切换 Embedding 模型前必须运行，清空所有旧向量（⚠️ 不可逆）"""
import os, time
from dotenv import load_dotenv
from pinecone import Pinecone
load_dotenv()

def main():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    host = os.getenv("PINECONE_HOST", "")
    index = pc.Index(host=host) if host else pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    total = index.describe_index_stats().total_vector_count
    print(f"当前向量数: {total}")
    if total == 0:
        print("Index 已为空。")
        return
    confirm = input(f"\n⚠️ 将删除全部 {total} 个向量，不可逆！输入 'yes' 确认: ")
    if confirm.strip().lower() != "yes":
        print("已取消。")
        return
    index.delete(delete_all=True)
    time.sleep(3)
    print(f"✅ 清空完成，当前向量数: {index.describe_index_stats().total_vector_count}")

if __name__ == "__main__":
    main()
```

### 10.1 系统提示词 (`backend/prompts/system_prompt.py`)

```python
BASE_SYSTEM_PROMPT = """你是一位专业的初中英语辅导老师，专门帮助八年级学生学习人教版英语教材。

## 你的角色
- 名字：英语老师小英（English Teacher Xiaoying）
- 专业：人教版八年级英语上下册（Go for it! Grade 8）
- 风格：耐心、鼓励、用简单易懂的中文解释英语知识

## 行为规则
1. **优先使用教材内容**：回答问题时，优先引用下面提供的教材原文内容
2. **中英双语**：解释用中文，英语例句保留英文
3. **适合年龄**：用13-14岁学生能理解的语言，避免过于学术化的术语
4. **鼓励式反馈**：即使学生答错了，也先肯定努力再纠正
5. **简洁明了**：回答控制在300字以内，除非是详细讲解请求
6. **引用来源**：回答完毕后，用这种格式注明出处：【来源：Unit X, Section X, 第X页】

## 当教材内容不足时
如果教材上下文与问题不相关，可以用你的英语教学知识回答，但要标注：【超出教材范围的补充说明】

## 教材上下文
{context}
"""

GRAMMAR_PROMPT_ADDITION = """
## 语法讲解格式
每次讲解语法点时，必须包含：
1. **定义**：一句话说明这个语法点是什么
2. **结构**：用公式表示（如：主语 + had + 过去分词）
3. **教材例句**：引用教材中的例句（如有）
4. **补充例句**：再给2个贴近生活的例句
5. **易错点**：指出学生常见的错误
"""

QUIZ_PROMPT_ADDITION = """
## 出题模式
你现在是一位出卷老师。严格按照指定格式输出JSON，不要有其他文字。
"""

CONVERSATION_PROMPT_ADDITION = """
## 对话练习模式
1. 扮演对话练习的搭档
2. 如果学生说了不自然或错误的英语，先继续对话，在对话结束后统一给出纠正建议
3. 在对话中自然地引入教材中的词汇和句型
4. 对话结束时给出评分（满分10分）和具体建议
"""

def build_system_prompt(
    mode: str = "general",
    context: str = "",
    student_level: str = "grade8"
) -> str:
    prompt = BASE_SYSTEM_PROMPT.format(context=context or "（未检索到相关教材内容）")
    
    if mode == "grammar":
        prompt += GRAMMAR_PROMPT_ADDITION
    elif mode == "quiz":
        prompt += QUIZ_PROMPT_ADDITION
    elif mode == "conversation":
        prompt += CONVERSATION_PROMPT_ADDITION
    
    return prompt
```

### 10.2 出题提示词 (`backend/prompts/quiz_prompt.py`)

```python
QUIZ_PROMPTS = {
    "multiple_choice": """
基于{unit}的教材内容，生成{count}道四选一选择题，难度：{difficulty}。

严格按以下JSON格式输出，不要添加任何其他文字：
```json
[
  {{
    "id": "q1",
    "type": "multiple_choice",
    "question": "题目（可以是中文或英文）",
    "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
    "answer": "A",
    "explanation": "解析（中文，说明为什么选A，以及其他选项错在哪里）",
    "unit": "{unit}",
    "difficulty": "{difficulty}"
  }}
]
```
""",
    
    "fill_blank": """
基于{unit}的教材内容，生成{count}道填空题，难度：{difficulty}。

严格按以下JSON格式输出：
```json
[
  {{
    "id": "q1",
    "type": "fill_blank",
    "question": "We ___ (go) to school every day. (用括号中动词的正确形式填空)",
    "answer": "go",
    "explanation": "一般现在时，主语是we，动词用原形",
    "unit": "{unit}",
    "difficulty": "{difficulty}"
  }}
]
```
""",
    
    "translation": """
基于{unit}的教材内容，生成{count}道翻译题（中英互译各半），难度：{difficulty}。

严格按以下JSON格式输出：
```json
[
  {{
    "id": "q1",
    "type": "translation",
    "question": "请将下面的中文翻译成英文：我昨天去了图书馆。",
    "answer": "I went to the library yesterday.",
    "explanation": "过去时态，go的过去式是went",
    "unit": "{unit}",
    "difficulty": "{difficulty}"
  }}
]
```
""",

    "grammar_correction": """
基于{unit}的语法点，生成{count}道语法纠错题，难度：{difficulty}。
每道题包含一个有语法错误的句子，让学生找出并改正。

严格按以下JSON格式输出：
```json
[
  {{
    "id": "q1",
    "type": "grammar_correction",
    "question": "找出并改正下面句子中的语法错误：She don't like apples.",
    "answer": "She doesn't like apples. (don't → doesn't，第三人称单数用doesn't)",
    "explanation": "主语是第三人称单数she，否定形式要用doesn't，not don't",
    "unit": "{unit}",
    "difficulty": "{difficulty}"
  }}
]
```
"""
}
```

---

## 11. 功能模块详细规格

### 11.1 数据模型 (`backend/models/request_models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    role: MessageRole
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[Message] = Field(default=[])
    mode: Literal["general", "grammar", "vocabulary", "conversation", "quiz"] = "general"
    unit_filter: Optional[str] = None
    semester_filter: Optional[Literal[1, 2]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Unit 3的过去进行时怎么用？",
                "history": [],
                "mode": "grammar",
                "unit_filter": "Unit 3",
                "semester_filter": 1
            }
        }

class QuizGenerateRequest(BaseModel):
    unit: str
    semester: Literal[1, 2]
    quiz_type: Literal["multiple_choice", "fill_blank", "translation", "grammar_correction"] = "multiple_choice"
    count: int = Field(default=5, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"

class GradeAnswerRequest(BaseModel):
    question: dict
    student_answer: str

class ProgressSaveRequest(BaseModel):
    user_id: str
    unit: str
    semester: int
    activity_type: Literal["quiz", "vocabulary", "conversation", "reading"]
    score: Optional[float] = None
    time_spent_seconds: Optional[int] = None
```

### 11.2 数据库设计 (`database/schema.sql`)

```sql
-- 用户表（简化版，不需要认证）
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对话历史表
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    mode TEXT DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 学习进度表
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    semester INTEGER NOT NULL CHECK(semester IN (1, 2)),
    activity_type TEXT NOT NULL,
    score REAL,
    time_spent_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 词汇掌握情况表
CREATE TABLE IF NOT EXISTS vocab_mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    word TEXT NOT NULL,
    unit TEXT NOT NULL,
    mastery_level INTEGER DEFAULT 0 CHECK(mastery_level BETWEEN 0 AND 5),
    review_count INTEGER DEFAULT 0,
    last_reviewed_at TIMESTAMP,
    next_review_at TIMESTAMP,  -- 间隔重复算法
    UNIQUE(user_id, word),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 测试记录表
CREATE TABLE IF NOT EXISTS quiz_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    semester INTEGER NOT NULL,
    quiz_type TEXT NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_count INTEGER NOT NULL,
    score REAL NOT NULL,
    questions_json TEXT,  -- 存储完整题目JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_progress_user ON progress(user_id, unit);
CREATE INDEX IF NOT EXISTS idx_vocab_user ON vocab_mastery(user_id, next_review_at);
```

---

## 12. API 接口文档

### 12.1 完整接口清单

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat/stream` | 流式对话 |
| POST | `/api/chat/sync` | 同步对话 |
| POST | `/api/quiz/generate` | 生成测试题 |
| POST | `/api/quiz/grade` | 批改答案 |
| GET | `/api/vocabulary/{semester}/{unit}` | 获取单元词汇 |
| POST | `/api/vocabulary/quiz` | 词汇测试 |
| GET | `/api/progress/{user_id}` | 获取学习进度 |
| POST | `/api/progress/save` | 保存学习记录 |
| GET | `/api/progress/{user_id}/weak-points` | 获取薄弱点分析 |

### 12.2 关键接口详细说明

**POST `/api/chat/stream`** — 流式对话

```
Request Body:
{
  "message": "string",          // 用户消息
  "history": [                  // 历史消息（最多20条）
    {"role": "user", "content": "string"},
    {"role": "assistant", "content": "string"}
  ],
  "mode": "general",            // general|grammar|vocabulary|conversation
  "unit_filter": "Unit 3",      // 可选，过滤单元
  "semester_filter": 1          // 可选，1或2
}

Response: text/event-stream
data: {"type": "text", "content": "Hello"}
data: {"type": "text", "content": " world"}
data: {"type": "done", "sources": [{"unit": "Unit 3", "page_num": 45, ...}]}
```

**POST `/api/quiz/generate`** — 生成题目

```
Request Body:
{
  "unit": "Unit 3",
  "semester": 1,
  "quiz_type": "multiple_choice",
  "count": 5,
  "difficulty": "medium"
}

Response: 200 OK
[
  {
    "id": "q1",
    "type": "multiple_choice",
    "question": "...",
    "options": ["A...", "B...", "C...", "D..."],
    "answer": "A",
    "explanation": "...",
    "unit": "Unit 3",
    "difficulty": "medium"
  }
]
```

---

## 13. 部署方案

### 13.1 本地开发启动

```bash
# 0. 环境准备（只做一次）
brew install pyenv
pyenv install 3.11.9
pyenv local 3.11.9          # 在项目目录下生效
python3 -m venv .venv
source .venv/bin/activate   # 每次进入项目先激活
# 验证：python3 -c "import torch; print(torch.backends.mps.is_available())" → True

# 1. 安装依赖
pip install easyocr pymupdf                   # OCR，约 2GB
pip install -r requirements.txt               # 其余依赖

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入以下关键值：
#   ANTHROPIC_API_KEY=sk-ant-...
#   PINECONE_API_KEY=...
#   PINECONE_INDEX_NAME=xsjkndb01
#   PINECONE_HOST=xsjkndb01-f408jww.svc.aped-4627-b74a...
#   EMBEDDING_MODEL=intfloat/multilingual-e5-large
#   EMBEDDING_DIMENSION=1024

# 3. 数据处理（只需运行一次，约 20-35 分钟）
# 将 PDF 放入 data/raw/
python scripts/00a_pdf_to_images.py    # 自动检测原生/扫描版

# OCR 二选一（PaddleOCR 禁用）：
python scripts/00b_ocr_with_minimax.py # 方案B：MiniMax M3 Vision（推荐，有配额）
# python scripts/00b_ocr_with_easyocr.py # 方案A：EasyOCR（无API时使用）

python scripts/00c_verify_ocr.py       # 验证质量（必做）
python scripts/02_chunk_text.py
python scripts/03_embed_and_upload.py
python scripts/04_verify_pinecone.py

# 4. 初始化数据库
mkdir -p database
sqlite3 database/app.db < database/schema.sql

# 5. 启动后端
uvicorn backend.main:app --reload --port 8000

# 6. 启动前端（新终端，同样先 source .venv/bin/activate）
cd frontend && npm install && npm run dev
# 访问 http://localhost:3000
```

### 13.2 Makefile 快捷命令

```makefile
.PHONY: env setup ocr pipeline backend frontend test

# 环境准备（只做一次）
env:
	pyenv install 3.11.9 || true
	pyenv local 3.11.9
	python3 -m venv .venv
	@echo "✅ Run: source .venv/bin/activate"

setup:
	pip install easyocr pymupdf
	pip install -r requirements.txt
	cd frontend && npm install
	mkdir -p database data/raw data/processed data/images data/ocr_cache
	cp .env.example .env
	@echo "⚠️  Edit .env: PINECONE_API_KEY / PINECONE_HOST / ANTHROPIC_API_KEY"

# 数据处理（一次性，扫描版PDF）
# ⚠️ 必须在 .venv 激活状态下运行：source .venv/bin/activate
ocr:
	python scripts/00a_pdf_to_images.py
	python scripts/00b_ocr_with_easyocr.py
	python scripts/00c_verify_ocr.py

pipeline: ocr
	python scripts/02_chunk_text.py
	python scripts/03_embed_and_upload.py
	python scripts/04_verify_pinecone.py

backend:
	uvicorn backend.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest tests/ -v

build:
	cd frontend && npm run build

docker-up:
	docker-compose up -d
```

### 13.3 Railway 部署（可选，免费层）

**后端 `railway.json`**:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/health"
  }
}
```

**前端 `vercel.json`**:
```json
{
  "env": {
    "NEXT_PUBLIC_API_URL": "https://your-backend.railway.app"
  }
}
```

---

## 14. 测试规格

### 14.1 RAG 服务测试 (`tests/test_rag_service.py`)

```python
import pytest
from backend.services.rag_service import RAGService

@pytest.fixture
def rag():
    return RAGService()

def test_retrieve_basic(rag):
    """基本检索功能"""
    results = rag.retrieve("past tense")
    assert len(results) > 0
    assert all("text" in r for r in results)
    assert all(r["score"] >= 0.3 for r in results)

def test_retrieve_with_unit_filter(rag):
    """单元过滤"""
    results = rag.retrieve("vocabulary", filter_unit="Unit 1")
    for r in results:
        assert r["unit"] == "Unit 1"

def test_retrieve_with_semester_filter(rag):
    """学期过滤"""
    results = rag.retrieve("grammar", filter_semester=1)
    for r in results:
        assert r["semester"] == 1

def test_format_context(rag):
    """上下文格式化"""
    chunks = [{"text": "Hello world", "unit": "Unit 1", "section": "A", "page_num": 5, "semester": 1, "score": 0.9}]
    context = rag.format_context(chunks)
    assert "Unit 1" in context
    assert "Page 5" in context

def test_chinese_query(rag):
    """中文查询也能检索到内容"""
    results = rag.retrieve("过去进行时")
    assert len(results) > 0
```

### 14.2 出题服务测试 (`tests/test_quiz_service.py`)

```python
import pytest
from backend.services.quiz_service import QuizService

@pytest.fixture
def quiz():
    return QuizService()

def test_generate_multiple_choice(quiz):
    questions = quiz.generate_quiz("Unit 1", 1, "multiple_choice", 3)
    assert len(questions) == 3
    for q in questions:
        assert q["type"] == "multiple_choice"
        assert "options" in q
        assert len(q["options"]) == 4
        assert q["answer"] in ["A", "B", "C", "D"]

def test_grade_correct_answer(quiz):
    question = {
        "type": "multiple_choice",
        "answer": "A",
        "explanation": "Test"
    }
    result = quiz.grade_answer(question, "A")
    assert result["is_correct"] == True
    assert result["score"] == 1.0

def test_grade_wrong_answer(quiz):
    question = {
        "type": "multiple_choice",
        "answer": "A",
        "explanation": "Test"
    }
    result = quiz.grade_answer(question, "B")
    assert result["is_correct"] == False
    assert result["score"] == 0.0
```

---

## 15. 开发顺序与里程碑

### Phase 0：环境准备（今天，约 30 分钟）

**目标**：开发环境就绪，CLAUDE.md + AGENTS.md 配置完成

```
✅ Step 1: 安装 pyenv + 创建虚拟环境（不用 Anaconda）
           brew install pyenv
           pyenv install 3.11.9 && pyenv local 3.11.9
           python3 -m venv .venv && source .venv/bin/activate

✅ Step 2: 配置 Karpathy skill + 全局 CLAUDE.md
           mkdir -p ~/.claude/skills
           curl -o ~/.claude/skills/karpathy.md \
             https://raw.githubusercontent.com/forrestchang/andrej-karpathy-skills/main/CLAUDE.md
           # 创建 ~/.claude/CLAUDE.md，内容：@~/skills/karpathy.md + M1环境说明

✅ Step 3: 项目初始化
           mkdir -p english-agent/data/raw
           cd english-agent
           echo "@AGENTS.md" > CLAUDE.md
           cp .env.example .env
           # 填入 PINECONE_API_KEY / PINECONE_HOST / ANTHROPIC_API_KEY

✅ Step 4: 把两个 PDF 放入 data/raw/，确认文件名
✅ 交付物：source .venv/bin/activate 激活，python3 -c "import torch; print(torch.backends.mps.is_available())" 输出 True
```

### Phase 1：数据基础（约 1 天，M1 本地跑）

**目标**：OCR + 向量化完成，Pinecone `xsjkndb01` 数据就绪

```
✅ Step 0: 安装依赖
           pip install pymupdf openai tenacity   # MiniMax OCR 必须
           pip install easyocr                   # 仅方案A需要（约2GB）
           pip install -r requirements.txt        # 其余依赖

✅ Step 1: 运行 00a_pdf_to_images.py
           - 10.7MB 文件：自动检测为原生 PDF，直接提取文字，跳到 Step 4
           - 241.8MB 文件：转为 PNG 图片（约 5 分钟，200 DPI）
           ⚠️ 禁止使用 PaddleOCR（macOS 13 Ventura + M1 卡死 bug，GitHub #10839）

✅ Step 2: 运行 OCR（二选一）
           方案B（推荐，有 MiniMax Token Plan）：
             python scripts/00b_ocr_with_minimax.py  （约 10-20 分钟，质量更好）
           方案A（无API配额）：
             python scripts/00b_ocr_with_easyocr.py  （约 20-35 分钟，完全免费）
           # 两个脚本输出格式完全相同，后续步骤一致
           # 有断点续传，中途中断重跑自动跳过已处理页

✅ Step 3: 运行 00c_verify_ocr.py，人工抽查 10 页 OCR 质量（必做，不可跳过）
✅ Step 4: 运行 02_chunk_text.py（约 1 分钟）
✅ Step 5: 运行 03_embed_and_upload.py（M1 MPS 加速，约 2-3 分钟）
✅ Step 6: 运行 04_verify_pinecone.py，验证中英文检索各 3 个
✅ 交付物：xsjkndb01 中有 500-700 个高质量向量，中英文检索均正常
```

### Phase 2：后端核心（2-3天）

**目标**：RAG + Claude 对话 API 可用

```
✅ Step 1: 创建目录结构，配置 .env
✅ Step 2: 实现 config.py, dependencies.py
✅ Step 3: 实现 rag_service.py，本地测试检索
✅ Step 4: 实现 agent_service.py，测试同步对话
✅ Step 5: 实现 chat.py 路由（先做同步接口）
✅ Step 6: 启动 uvicorn，用 curl 测试 /api/chat/sync
✅ Step 7: 实现流式接口 /api/chat/stream
✅ 交付物：后端 API 可通过 curl/Postman 验证
```

### Phase 3：出题与词汇（1-2天）

```
✅ Step 1: 实现 quiz_service.py
✅ Step 2: 实现 quiz.py 路由
✅ Step 3: 实现基础进度存储（SQLite）
✅ 交付物：可以生成并批改测试题
```

### Phase 4：前端界面（2-3天）

**目标**：完整可用的学习界面

```
✅ Step 1: 创建 Next.js 项目，配置 Tailwind
✅ Step 2: 实现 api.ts 客户端
✅ Step 3: 实现聊天页面（useChat hook + ChatWindow 组件）
✅ Step 4: 实现测试页面（QuizCard 组件）
✅ Step 5: 实现进度页面（简单图表）
✅ 交付物：完整的学习界面
```

### Phase 5：优化与发布（1-2天）

```
✅ 性能优化：嵌入模型预热，响应缓存
✅ 错误处理：API 失败重试，用户友好提示
✅ 部署：Railway（后端）+ Vercel（前端）
✅ 交付物：可访问的线上地址
```

> **以下 §16-§20 为 v2.2 之后追加的开发记录**，覆盖 Phase 2-6 的实际实现。所有新增模块均遵循 AGENTS.md 规范，遵守 E5 前缀规范、禁用 PaddleOCR、分步开发等核心规则。

---

## 16. Phase 2 — 出题/批改模块

### 16.1 目标

基于教材内容自动出题（单选/填空/翻译），并对学生的回答进行自动批改。

### 16.2 新增文件

| 文件 | 职责 |
|------|------|
| `backend/prompts/quiz_prompt.py` | 出题 prompt + 批改 prompt 模板 |
| `backend/services/quiz_service.py` | 出题和批改的核心业务逻辑 |
| `backend/routers/quiz.py` | HTTP 路由 |

### 16.3 关键实现细节

#### 16.3.1 出题 Prompt

`QUIZ_GENERATION_PROMPT` 模板要求 MiniMax M3 **严格按 JSON 数组输出**，每道题包含 id/type/question/options/answer/explanation 五个字段。

**重要坑位（已修复）**：

```
MiniMax M3 默认会先输出 <think>...</think> 推理块，再跟 JSON。
如果不剥离，json.loads() 会报 JSONDecodeError。
```

修复方案（在 `quiz_service.py` 的 `parse_json_response` 中）：

```python
def parse_json_response(content: str) -> dict | list:
    content = content.strip()
    if "<think>" in content:
        end = content.find("</think>")
        if end != -1:
            content = content[end + len("</think>"):].strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)
```

#### 16.3.2 批改快路径

单选题做大小写归一化（`student.upper() == correct.upper()`），直接返回 1.0 分，不调 LLM。填空题/翻译题调 LLM 批改。

#### 16.3.3 API 规格

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/api/quiz/generate` | POST | `{unit, semester, quiz_type, count, difficulty}` | `{questions: [...]}` |
| `/api/quiz/grade` | POST | `{question, student_answer, unit, semester}` | `{is_correct, score, feedback, correction}` |

### 16.4 端到端测试

curl 验证：生成 2 道 Unit 1 单选题（基于 Teng Fei 访谈和 Emma 滑冰的教材原文），批改对/错各 1 道题，JSON 格式正确，LLM 反馈包含中文解析。

---

## 17. Phase 3 — 前端聊天界面

### 17.1 目标

搭好前端基础，实现聊天页面的端到端可用。

### 17.2 技术栈

- Next.js 14.2（App Router）
- TypeScript
- Tailwind CSS 3
- 额外依赖：`react-markdown`、`remark-gfm`、`lucide-react`、`framer-motion`、`@tailwindcss/typography`

### 17.3 新增文件

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # 聊天主页面
│   ├── globals.css             # Tailwind base
│   └── login/                  # Phase 6 补加
├── components/
│   └── chat/
│       ├── MessageBubble.tsx   # 消息气泡（Markdown 渲染）
│       ├── SourcePanel.tsx     # 来源引用面板
│       └── InputBar.tsx        # 输入栏
├── hooks/
│   └── useChat.ts              # 聊天状态管理
└── lib/
    ├── types.ts                # TypeScript 类型
    └── api.ts                  # API 客户端（含 SSE 解析）
```

### 17.4 关键实现

#### 17.4.1 SSE 流式解析

`lib/api.ts` 中的 `chatStream` 使用 `ReadableStream` + `TextDecoder` 逐块解析 SSE：

```typescript
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n\n");
  buffer = lines.pop() ?? "";
  for (const line of lines) {
    if (!line.startsWith("data: ")) continue;
    const event: StreamEvent = JSON.parse(line.slice(6).trim());
    if (event.type === "text") onText(event.content);
    else if (event.type === "done") onDone(event.sources);
  }
}
```

#### 17.4.2 流式光标

`MessageBubble` 组件在 `streaming: true && content` 时显示一个 `animate-pulse` 的灰色光标，模拟打字机效果。

#### 17.4.3 Markdown 渲染

AI 回答用 `react-markdown` + `remark-gfm` 渲染，GFM 表格支持来自 `remark-gfm`。`@tailwindcss/typography` 提供 `prose` 样式。

### 17.5 端到端测试

1. 启动后端（`uvicorn backend.main:app --port 8000`）
2. 启动前端（`cd frontend && npm run dev`）
3. 浏览器打开 `http://localhost:3000`
4. 发送"Unit 1 的 Grammar Focus 讲什么语法？"，流式输出 + 来源引用正常

---

## 18. Phase 4 — 出题与词汇前端

### 18.1 范围调整说明

**v2.2 原计划：** Phase 2（出题后端） → Phase 3（前端聊天）→ Phase 4（出题前端）  
**实际执行：** Phase 2 仅包含出题/批改后端（§16），Phase 3 仅包含聊天前端（§17），Phase 4 同时包含出题前端和词汇前端。

### 18.2 新增文件

```
frontend/
├── app/quiz/page.tsx              # 随堂测试主页面
└── components/quiz/
    └── QuizCard.tsx               # 题目卡片（单选/填空/翻译通用）
```

### 18.3 QuizCard 设计

支持三种题型的统一组件：
- **单选题**：渲染 A/B/C/D 按钮，选中后高亮，批改后正确选项绿、错误选项红
- **填空题/翻译题**：textarea 输入
- **批改后展开区**：对错图标 + 分数 + 中文反馈 + 正确答案 + 教材解析 + "重做" / "下一题" 按钮

### 18.4 流程

1. 用户在 `/quiz` 选择学期/单元/题型/题数/难度
2. 点击"开始测试"，调用 `/api/quiz/generate` 拉题目
3. 逐题作答，每题调 `/api/quiz/grade`
4. 全部答完显示总分（绿色卡片"答对"+ 灰色卡片"答错"）
5. 单元/学期上下文（unit, semester）通过 props 传到 QuizCard，批改时一并提交后端

---

## 19. Phase 5 — 学习进度与词汇后端

### 19.1 目标

实现两个能力：
- 学习进度：自动记录每次答题结果，统计总题数/正确率/薄弱单元
- 词汇表：从教材 OCR 提取词汇，供前端闪卡练习使用

### 19.2 新增文件

| 文件 | 职责 |
|------|------|
| `backend/models/db_models.py` | SQLAlchemy 异步 ORM（User/QuizRecord/VocabProgress） |
| `backend/services/progress_service.py` | 进度保存/查询/统计 |
| `backend/services/vocab_service.py` | 词汇表加载/查询/随机抽题 |
| `backend/routers/progress.py` | 进度相关 HTTP 路由 |
| `backend/routers/vocabulary.py` | 词汇相关 HTTP 路由 |
| `scripts/extract_vocab.py` | 从 OCR 文本提取教材词汇 |

### 19.3 数据库设计

```sql
-- SQLite via SQLAlchemy + aiosqlite
users (id, username UNIQUE, password_hash, display_name, created_at)
quiz_records (id, user_id, unit, semester, quiz_type, question_text,
              student_answer, correct_answer, is_correct, score, created_at)
vocab_progress (id, user_id, word, unit, semester,
                mastery_level 0-3, review_count, last_reviewed)
```

外键全部 `ON DELETE CASCADE`，用户删除时数据一起清。

### 19.4 关键模块

#### 19.4.1 数据库初始化

在 `main.py` 的 `lifespan` 中加 `await init_db()`，应用启动时自动建表（`Base.metadata.create_all`）。

#### 19.4.2 进度摘要

`get_progress_summary(user_id)` 返回：
- `total`、`correct`、`accuracy`、`avg_score`
- `weak_units`：按正确率升序的 Top 3 单元

#### 19.4.3 词表提取

`scripts/extract_vocab.py` 扫描 `data/processed/raw_pages_*.json`，识别含"Vocabulary"章节的页面，用正则提取 `word /phonetic/ pos. translation` 格式的词条，按 unit 分组去重。

**已知问题**：OCR 阶段 Unit 125 误识别导致部分 Vocabulary 页归到错误的 Unit，词表准确率受 OCR 质量影响（Phase 7 待优化项）。

### 19.5 关键坑位（已解决）

| 坑位 | 解决 |
|------|------|
| `ModuleNotFoundError: No module named 'greenlet'` | `pip install greenlet`（SQLAlchemy 异步必需） |
| 切换数据库 schema 后旧数据 FK 不匹配 | 删除 `database/app.db` 重建（开发期） |

### 19.6 集成点

`backend/routers/quiz.py` 的 `/grade` 接口在批改后自动调用 `save_quiz_record()`，**无需前端额外调用**。

---

## 20. Phase 6 — 多用户系统

### 20.1 目标

从单用户（无认证）升级到完整多用户：注册/登录、JWT token、进度隔离。

### 20.2 新增文件

| 文件 | 职责 |
|------|------|
| `backend/services/auth_service.py` | 密码 hash、用户 CRUD、JWT 签发/验证 |
| `backend/routers/auth.py` | 注册/登录/me 路由 + `get_current_user` 依赖 |

### 20.3 改造的现有文件

| 文件 | 改动 |
|------|------|
| `backend/models/db_models.py` | 加 User 表，quiz_records / vocab_progress 加 user_id 外键 |
| `backend/services/progress_service.py` | 所有函数加 user_id 参数 |
| `backend/routers/quiz.py` | `/grade` 加 `Depends(get_current_user)` |
| `backend/routers/progress.py` | 所有路由加 `Depends(get_current_user)` |
| `backend/main.py` | 注册 auth 路由 |

### 20.4 认证机制

#### 20.4.1 密码存储

```python
# 注册时
salt = secrets.token_hex(16)
digest = hashlib.sha256((salt + password).encode()).hexdigest()
stored = f"{salt}${digest}"   # 存数据库

# 登录时
expected = hashlib.sha256((salt + password).encode()).hexdigest()
return hmac.compare_digest(digest, expected)   # 防时序攻击
```

#### 20.4.2 JWT Token

- 算法：HS256
- Payload：`{sub: user_id, username, iat, exp}`（30 天有效）
- Secret：从 `.env` 的 `JWT_SECRET` 读，默认用 `app_secret_key`

#### 20.4.3 关键坑位（已解决）

```
InvalidSubjectError: Subject must be a string
```

pyjwt 新版本要求 `sub` claim 必须是字符串。**修复**：签发时用 `str(user_id)`，解析时用 `int(payload["sub"])`。

### 20.5 依赖注入

```python
def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:].strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    return {"id": int(payload["sub"]), "username": payload["username"]}
```

在受保护的路由上 `Depends(get_current_user)` 即可。

### 20.6 前端改动

| 文件 | 改动 |
|------|------|
| `frontend/lib/auth.ts` | localStorage 存 token、saveAuth/clearAuth、login/register 函数 |
| `frontend/hooks/useAuth.ts` | 路由守卫 hook（未登录跳 `/login`） |
| `frontend/lib/api.ts` | 所有受保护接口通过 `authHeaders()` 自动加 `Authorization: Bearer <token>` |
| `frontend/app/login/page.tsx` | 登录/注册 Tab 切换页 |
| `frontend/app/page.tsx`、`quiz`、`vocabulary`、`progress` | 加 `useAuth` 守卫、侧边栏显示用户名和退出按钮 |

### 20.7 端到端测试

curl 验证多用户隔离：
1. 注册 alice、bob
2. alice 做 2 道题，bob 做 1 道题
3. alice 看 summary：total=2, correct=1
4. bob 看 summary：total=1, correct=0
5. 互不干扰 ✅

---

## 附录 C：项目当前完整状态

### 当前功能矩阵（v3.0）

| 功能 | 状态 | 入口 |
|------|------|------|
| PDF 转图片（自动检测原生） | ✅ | `scripts/00a_pdf_to_images.py` |
| OCR（MiniMax M3 Vision） | ✅ | `scripts/00b_ocr_with_minimax.py` |
| OCR 质量验证 | ✅ | `scripts/00c_verify_ocr.py` |
| 文本分块 | ✅ | `scripts/02_chunk_text.py` |
| 向量化 + 上传 Pinecone | ✅ | `scripts/03_embed_and_upload.py` |
| Pinecone 检索验证 | ✅ | `scripts/04_verify_pinecone.py` |
| 词汇表提取 | ✅ | `scripts/extract_vocab.py` |
| 聊天对话（流式 + 来源） | ✅ | `/api/chat/stream` |
| 出题（3 种题型） | ✅ | `/api/quiz/generate` |
| 自动批改 | ✅ | `/api/quiz/grade` |
| 进度统计（个人） | ✅ | `/api/progress/*` |
| 词汇闪卡（个人） | ✅ | `/api/vocab/*` |
| 多用户注册/登录 | ✅ | `/api/auth/*` |
| 前端聊天 UI | ✅ | `/` |
| 前端出题 UI | ✅ | `/quiz` |
| 前端词汇 UI | ✅ | `/vocabulary` |
| 前端进度 UI | ✅ | `/progress` |
| 前端登录 UI | ✅ | `/login` |

### 当前数据状态

- Pinecone `xsjkndb01`：841 个向量（1024维）
- 教材：八年级上册（146 页原生 PDF） + 下册（146 页 MiniMax OCR）
- 词汇：114 个词（受 OCR 质量影响，部分 Unit 归类不准确）
- 数据库：3 张表（users / quiz_records / vocab_progress），开发期可随时清空

### 待优化项

1. OCR 阶段 Unit 125 误识别（页码 125 误判为单元号），影响词表归类准确度
2. 词汇练习缺少 SM-2 / 间隔重复算法
3. 前端无响应式优化（移动端体验差）
4. 未做 Docker 部署 / Railway / Vercel
5. 未做对话历史持久化（当前只在内存中）

---

## 21. Phase 7 — 对话历史持久化

### 21.1 目标

解决对话历史刷新页面丢失的问题。引入 `chat_sessions` 和 `chat_messages` 两张表，所有用户消息和 AI 回答都持久化到 SQLite，支持：
- 刷新页面 / 切换功能 / 关闭浏览器再打开，对话不丢
- 多会话并存（侧边栏列出会话列表）
- 自动从首条用户消息生成会话标题
- 多用户隔离（每个用户只看自己的会话）
- 跨设备/跨账号同步（数据库存储而非 localStorage）

### 21.2 新增文件

| 文件 | 职责 |
|------|------|
| `backend/services/chat_history_service.py` | 会话/消息 CRUD 业务逻辑 |
| `backend/routers/history.py` | `/api/history/*` 4 个 HTTP 端点 |

### 21.3 数据库设计

```sql
chat_sessions (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(200) DEFAULT '新对话',
  created_at DATETIME,
  updated_at DATETIME  -- 自动更新（onupdate）
)
chat_messages (
  id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role VARCHAR(20),  -- 'user' | 'assistant'
  content TEXT,
  sources_json TEXT DEFAULT '[]',
  created_at DATETIME
)
```

外键全部 `ON DELETE CASCADE`，用户删除时连同会话/消息一起清。

### 21.4 关键实现

#### 21.4.1 自动标题生成

`save_message` 内：
```python
if chat_session.title == "新对话" and role == "user":
    chat_session.title = content[:30] + ("..." if len(content) > 30 else "")
```

首条用户消息自动成为会话标题。

#### 21.4.2 Chat 路由集成

`/api/chat/sync` 和 `/api/chat/stream` 都支持可选的 `session_id`：

```python
async def _resolve_session(user_id: int, session_id: Optional[int]) -> int:
    if session_id:
        data = await get_session_with_messages(session_id, user_id)
        if not data:
            raise ValueError(f"Session {session_id} not found")
        return session_id
    return await create_session(user_id)
```

不传 `session_id` → 自动建新会话；传了 → 复用已存在会话。

流式接口的特殊处理：在 `generate()` 协程里先 yield 所有 text 块，**最后**再 `await save_message()`（因为 AI 完整内容要等所有 delta 拼起来）。

#### 21.4.3 关键坑位（已解决）

```
MiniMax M3 输出含 <think>...</think> 推理块，
直接存数据库会让用户回看时看到思考过程。
```

修复（`chat_history_service.save_message`）：
```python
if role == "assistant" and "<think>" in content:
    end = content.find("</think>")
    if end != -1:
        content = content[end + len("</think>"):].strip()
```

同样的 `parse_json_response` 函数也用了相同逻辑（quiz_service）。

#### 21.4.4 React Hooks 顺序问题

`app/page.tsx` 加 `useAuth` 守卫时，错误地把 `useEffect` 放在 `if (loading) return` 之后，触发：

```
Error: Rendered more hooks than during the previous render.
```

**修复规则**：所有 `useState` / `useEffect` / `useRef` 必须在所有 early return 之前调用。

### 21.5 API 规格

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/api/history/sessions` | GET | `?limit=50` | `[{id, title, created_at, updated_at}, ...]` |
| `/api/history/sessions` | POST | `{title}` | `{id, title}` |
| `/api/history/sessions/{id}` | GET | — | `{id, title, messages: [...]}` |
| `/api/history/sessions/{id}` | DELETE | — | `{ok: true}` |

全部需要登录，`user_id` 强制从 token 解析。

### 21.6 前端改造

| 文件 | 改动 |
|------|------|
| `frontend/lib/api.ts` | 新增 `listSessions` / `getSession` / `createSession` / `deleteSession`；`chatStream` 回调增加 `sessionId` 参数 |
| `frontend/hooks/useChat.ts` | 状态增加 `sessionId` / `sessionTitle`，新增 `loadSession(id)` 和 `startNew()`，发送时带 `session_id` |
| `frontend/app/page.tsx` | 侧边栏加"对话历史"区（列表 + 新建按钮 + 删除按钮），header 显示当前 session 标题 |

### 21.7 端到端测试

1. Alice 发 2 条消息 → 自动建 session 1
2. Alice 查 `/api/history/sessions` → 显示 1 个会话，标题是首条消息
3. Alice 查 session 1 → 显示 user 消息 + AI 消息 + 5 个 sources
4. Bob 查 sessions → 空（看不到 Alice 的）
5. Bob 直接 GET Alice 的 session → 404
6. 跨刷新、跨功能切换（聊天 → 词汇 → 聊天）→ 会话保留 ✅

### 21.8 文档/坑位同步

AGENTS.md §13 加 4 条新坑位：
- #19：M3 `<think>` 块需剥离
- #20：PyJWT `sub` claim 必须是字符串
- #21：React Hooks 早 return 顺序
- #22：SQLite 异步缺 greenlet

---

## 22. Phase 7+ — 对话模式标签

### 22.1 动机

Phase 7 实现了"所有模式共用同一 session 历史"。但用户实际使用中发现：聊天过程中切换模式后，历史消息变得无法分辨"当时用的什么模式"，对家长/老师复盘造成困难。

**决策**：在每条消息上记录"它是用哪个模式产生的"，UI 上显示一个小标签。这是 §15 阶段命名里的 "P7+" ——在已发布功能上做小增强，不算独立 Phase。

### 22.2 改动

| 文件 | 改动 |
|------|------|
| `backend/models/db_models.py` | `ChatMessage` 加 `mode: VARCHAR(20)` 字段 |
| `backend/services/chat_history_service.py` | `save_message(..., mode="")` 新参数；`get_session_with_messages` 返回值加 `mode` |
| `backend/routers/chat.py` | sync/stream 调 `save_message` 时传 `request.mode` |
| `frontend/lib/types.ts` | `Message` 接口加 `mode?: string` |
| `frontend/hooks/useChat.ts` | `loadSession` 时把历史消息的 `mode` 填到 Message |
| `frontend/components/chat/MessageBubble.tsx` | AI 消息上方显示 emoji+标签：`💡 通用` / `📖 语法` / `📝 出题` / `💬 对话` |

### 22.3 数据库迁移

加 `mode` 字段后，`Base.metadata.create_all` 不会自动给已有表加列。**开发期直接删 `database/app.db` 重建**。生产期需要用 Alembic 等迁移工具（待补）。

### 22.4 端到端测试

```bash
# 同一 session 依次发 3 条不同模式
curl -X POST /api/chat/sync -d '{"message":"...","mode":"grammar","session_id":1}'
curl -X POST /api/chat/sync -d '{"message":"...","mode":"quiz","session_id":1}'
curl -X POST /api/chat/sync -d '{"message":"...","mode":"conversation","session_id":1}'

# 查 session 应见 3 种 mode 标签
curl /api/history/sessions/1
# → 6 条消息，每条带正确 mode
```

前端：刷新页面后，AI 回答上方的标签保留，验证持久化成功。

### 22.5 文档同步

AGENTS.md 无新坑位（无新错误），开发文档同步本节。

---

## 23. Bug Fix 集锦

> 本节集中记录**非新功能但有重要修复**的 bug。原则：所有坑位（v1.4 列表 #1-#24）都应能在这里找到解决方案的代码级引用或决策说明。

### 23.1 React Hooks 早 return 顺序（坑位 #21）

**症状**：`Error: Rendered more hooks than during the previous render`

**根因**：`useAuth` 守卫 `if (loading) return <Spinner/>` 放在 `useState` / `useEffect` 之后，hooks 调用次数随 `loading` 状态变化，破坏 React 不变式。

**修复**：所有 `useState` / `useEffect` / `useRef` **必须**在所有 early return 之前调用。

```tsx
export default function QuizPage() {
  const [a, setA] = useState(...);  // 所有 useState 在前
  const [b, setB] = useState(...);
  // ...所有 hooks...
  const { loading } = useAuth();
  if (loading) return <Spinner/>;  // early return 在最后
  // ...业务代码...
}
```

**影响文件**：`frontend/app/page.tsx`、`quiz/page.tsx`、`vocabulary/page.tsx`、`progress/page.tsx`

### 23.2 useAuth 死循环 + 异常卡死（坑位 #21 衍生）

**症状**：
- 已在 `/login` 页时仍触发 `router.push("/login")` 形成 redirect 循环
- `getUser()` 抛异常（如 localStorage 数据损坏）时 `setLoading(false)` 永不执行，loading 卡死

**修复**：
- 用 `usePathname()` 判断，仅在非 `/login` 时 redirect
- `try/catch` 包住 `getUser()`，异常时 `clearAuth()` 并设 loading=false

### 23.3 SQLite 缺 greenlet 依赖（坑位 #22）

**症状**：`ValueError: the greenlet library is required to use this function.`

**修复**：`pip install greenlet`（SQLAlchemy 异步必需）。已加入 `requirements.txt`。

### 23.4 JWT `sub` claim 必须是字符串（坑位 #20）

**症状**：`InvalidSubjectError: Subject must be a string`

**修复**：签发用 `str(user_id)`，解析用 `int(payload["sub"])`。

### 23.5 ChatMessage 加 mode 字段后旧 db 报错（坑位 #21 衍生）

**症状**：`sqlite3.OperationalError: no such column: chat_messages.mode`

**修复**：开发期 `rm database/app.db` 重建。生产期需要用 Alembic 迁移（待补）。

### 23.6 quiz 出题 JSON 频繁截断（坑位 #23）★

**症状**：出题返回 500，`json.decoder.JSONDecodeError: Unterminated string` 或 `len=969` 等异常短。

**根因**：RAG 上下文（5 个 chunk × 500 字符 = 2500 字符） + 完整 prompt 模板 + 3 道题的 JSON 输出 ≈ 6000+ tokens，超过 `max_tokens=2048`，AI 输出被中途截断。

**修复 4 步组合**：

| 步骤 | 改动 | 效果 |
|------|------|------|
| 1. 减 RAG 上下文 | `top_k=2`（原 5） | prompt 长度减半 |
| 2. 简化 system prompt | "question≤50字，explanation≤20字，禁止 <think>" | 强制 AI 紧凑输出 |
| 3. `parse_json_response` 渐进式 trim | 找所有 `},` `]` 候选位置，逐一尝试解析 | 截断场景能恢复 1-2 题 |
| 4. retry 机制 | 失败时 `max_tokens=6000` 重试 | 给足空间输出完整 JSON |

**实测**：1/5 → 3/5 → **4/5 通过**。剩余 1/5 是偶发 API 抖动，UI 重试即可。

**RAG top_k 选型决策**详见 AGENTS.md §7.5。

### 23.7 grade 中文反馈里 ASCII 双引号破坏 JSON（坑位 #24）★

**症状**：`grade_answer` 返回 500，body 是 M3 返回的合法 JSON 但中文 `feedback` / `correction` 字段里用了 `"我想..."`（英文双引号）作为引用符号，JSON 解析器把字符串截断。

**修复 3 层防护**：

```python
# 1) parse_json_response 替换全角/智能引号
content = content.replace("“", "«").replace("”", "»") \
                 .replace("‘", "‹").replace("’", "›") \
                 .replace("「", "《").replace("」", "》")

# 2) system prompt 明确禁止中文里用双引号
"中文内容中**不要使用双引号**（包括 "" 和 ""），用「」或省略。"

# 3) grade 端点加 try/except fallback
try:
    return parse_json_response(...)
except (ValueError, json.JSONDecodeError):
    # 用 answer vs student_answer 匹配给默认结果，不让用户看到 500
    return {"is_correct": is_correct, ...}
```

**实测**：5/5 通过。

### 23.8 次要坑位汇总

| 现象 | 状态 |
|------|------|
| PyJWT `InsecureKeyLengthWarning: HMAC key 23 bytes < 32` | 警告非错误，`.env` 加长 `JWT_SECRET` 即可 |
| Next.js dev server 偶尔把 App Router 认成 Pages Router 致全 404 | `.next` 缓存损坏，`rm -rf .next` + 重启 |
| SQLite 加新字段后旧表结构不匹配 | 开发期删库重建，生产期待 Alembic |

---


---

## 附录 A：常见问题与解决方案

### Q0: macOS 13 Ventura + M1 关键禁忌（必读）

```
❌ 禁止使用 PaddleOCR / paddlepaddle
   原因：macOS Ventura + M1/M2 上调用 ocr() 进程直接卡死（hang），
         只能 kill -9，GitHub #10839/#13061，官方至今未修复
   替代：EasyOCR（pip install easyocr，M1 MPS 加速，完全正常）

❌ 禁止使用 Anaconda / conda 管理环境
   原因：M1 上 conda 历史包袱多，部分包仍走 Rosetta x86 模拟
   替代：pyenv + venv（brew install pyenv，python3 -m venv .venv）

❌ 禁止使用 Python 3.13
   原因：ML 生态（numba、tokenizers、ONNX）尚未完全跟进
   推荐：Python 3.11.x（最稳）或 3.12.x
```

### Q1: multilingual-e5-large 下载太慢

```bash
# 设置 HuggingFace 镜像（国内加速）
export HF_ENDPOINT=https://hf-mirror.com
python scripts/03_embed_and_upload.py
# 模型约 2.2GB，M1 下载后缓存在 ~/.cache/huggingface/
```

### Q1b: EasyOCR 模型下载失败

EasyOCR 模型从 GitHub Releases 下载，国内需要代理：
```bash
export HTTPS_PROXY=http://127.0.0.1:7890   # 替换为你的代理端口
python scripts/00b_ocr_with_easyocr.py
# 模型约 500MB，下载后存到 ~/.EasyOCR/model/，后续离线运行
```

### Q1c: 虚拟环境激活后 pip 还在用系统 Python

```bash
# 检查 pip 来源
which pip3   # 应该是 .venv/bin/pip3，不是 /usr/bin/ 或 /opt/homebrew/
which python3  # 应该是 .venv/bin/python3

# 如果不对，重新激活
deactivate
source .venv/bin/activate

# 验证 M1 MPS 可用
python3 -c "import torch; print(torch.backends.mps.is_available())"  # 应输出 True
```

### Q2: Pinecone 连接报错 "Index not found"

确认 `.env` 中三个值都正确：
```bash
PINECONE_INDEX_NAME=xsjkndb01
PINECONE_HOST=xsjkndb01-f408jww.svc.aped-4627-b74a...  # 从控制台复制完整 Host
PINECONE_ENVIRONMENT=us-east-1
```
建议优先用 Host 直连：`pc.Index(host=PINECONE_HOST)`，更稳定。

### Q3: 维度不匹配报错 `expected 1024`

所有嵌入操作必须用 `intfloat/multilingual-e5-large`（输出 1024 维）。
如果误用了其他模型（如 all-MiniLM-L6-v2 输出 384 维），上传时 Pinecone 会报错。
确认 `.env` 中 `EMBEDDING_MODEL=intfloat/multilingual-e5-large`。

### Q4: 查询结果相关性差

最常见原因是忘记加 E5 前缀。检查：
- 上传脚本：`f"passage: {chunk['text']}"` ✅
- 查询代码：`f"query: {user_input}"` ✅
两处都必须有前缀，缺一不可。

### Q5: Claude API 调用成本控制

```python
# 在 agent_service.py 中添加 token 计数日志
import logging
logger = logging.getLogger(__name__)

# 每次 API 调用后记录
logger.info(f"Tokens used: input={response.usage.input_tokens}, output={response.usage.output_tokens}")
# claude-haiku: $0.25/M input, $1.25/M output（2025年价格，以官网为准）
```

### Q6: 对话历史过长导致超出 context window

当 `conversation_history` 超过20轮时，`agent_service.py` 会自动截取最近10轮（20条消息）。
如需保留更长历史，可以实现"对话摘要"功能，将早期历史压缩成摘要再传入。

---

## 附录 B：人教版八年级教材单元列表

### 上册（Semester 1）
| 单元 | 主题 | 关键语法 |
|------|------|---------|
| Unit 1 | Where did you go on vacation? | 一般过去时 |
| Unit 2 | How often do you exercise? | 频率副词 |
| Unit 3 | I'm more outgoing than my sister. | 形容词比较级 |
| Unit 4 | What's the best movie theater? | 形容词最高级 |
| Unit 5 | Do you want to watch a game show? | 宾语从句 |
| Unit 6 | I'm going to study computer science. | be going to |
| Unit 7 | Will people have robots? | will + 动词原形 |
| Unit 8 | How do you make a banana milk shake? | 祈使句 |
| Unit 9 | Can you come to my party? | 情态动词 |
| Unit 10 | If you go to the party, you'll have a great time. | if 条件句 |

### 下册（Semester 2）
| 单元 | 主题 | 关键语法 |
|------|------|---------|
| Unit 1 | What's the matter? | 情态动词 should |
| Unit 2 | I'll help to clean up the city parks. | 不定式 |
| Unit 3 | Could you please clean your room? | 礼貌请求 |
| Unit 4 | Why don't you talk to your parents? | 提建议 |
| Unit 5 | What were you doing when the rainstorm came? | 过去进行时 |
| Unit 6 | An old man tried to move the mountains. | 一般过去时（阅读） |
| Unit 7 | What's the highest mountain in the world? | 间接引语 |
| Unit 8 | Have you read Treasure Island yet? | 现在完成时 |
| Unit 9 | Have you ever been to a museum? | 现在完成时 |
| Unit 10 | The future is coming! | 综合复习 |

---

*文档版本：v3.2 | 最后更新：2026-06-02*  
*变更：*
- *v3.2：追加 §22 Phase 7+（message mode 标签，UI 显示对话所用模式）和 §23 Bug Fix 集锦（8 个非功能性的重要修复汇总，含 quiz JSON 截断 4 步组合、grade 中文双引号 3 层防护、React Hooks 顺序等）；AGENTS.md 同步 4 条新坑位（#21-24）和 §7.5 RAG top_k 决策记录*
- *v3.1：追加 §21 Phase 7（对话历史持久化，chat_sessions + chat_messages 表，侧边栏会话列表）；同步 AGENTS.md 4 条新坑位（#19-22）*
- *v3.0：追加 §16-§20，覆盖 Phase 2-6 实现。出题/批改、前端聊天、出题前端、学习进度+词汇、多用户系统*
- *v2.2：新增 MiniMax M3 Vision OCR（方案B，利用 Token Plan ~0.5B tokens/月配额，脚本 00b_ocr_with_minimax.py）；OCR 方案由单一变为 A/B 双选*

*环境：macOS 13 Ventura / M1 16GB | Python 3.11（pyenv+venv）| MiniMax M3 OCR + EasyOCR备选 | multilingual-e5-large 1024维 | xsjkndb01 | MiniMax M3 对话模型（OpenAI 兼容接口）| SQLite + JWT*
