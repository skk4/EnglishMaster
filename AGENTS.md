# AGENTS.md — AI Agent 开发规范与避坑指南

> **适用范围**：所有基于 Claude API + RAG 架构的 Agent 项目（学习助手、客服 Agent、知识库问答等）  
> **运行环境**：macOS 13 Ventura / Apple M1 / 16GB RAM / Python 3.11  
> **经验来源**：初中英语 AI 学习 Agent 完整开发过程提炼（含 MiniMax M3 + Claude 多 AI 协作经验）  
> **维护原则**：每次踩坑后更新本文档，Claude Code 开发前必读

---

## 目录

1. [开发前必读：环境核查清单](#1-开发前必读环境核查清单)
2. [技术选型规则](#2-技术选型规则)
3. [Pinecone 使用规范](#3-pinecone-使用规范)
4. [Embedding 模型规范](#4-embedding-模型规范)
5. [OCR 规范（扫描文档场景）](#5-ocr-规范扫描文档场景)
6. [数据处理流水线规范](#6-数据处理流水线规范)
7. [RAG 架构规范](#7-rag-架构规范)
8. [Prompt 工程规范](#8-prompt-工程规范)
9. [后端 API 规范](#9-后端-api-规范)
10. [Claude Code 协作规范](#10-claude-code-协作规范)
11. [成本控制规范](#11-成本控制规范)
12. [国内网络规范](#12-国内网络规范)
13. [已知坑位速查表](#13-已知坑位速查表)
14. [新 Agent 项目启动模板](#14-新-agent-项目启动模板)

---

## 1. 开发前必读：环境核查清单

**每个新 Agent 项目开始前，逐项确认：**

```
[ ] 虚拟环境：pyenv + venv（不用 Anaconda/Conda）
    激活：source .venv/bin/activate  
    Python 路径确认：which python3 → 应指向 .venv/
[ ] Python 版本：3.11.x（不用 3.13，ML 生态尚未跟进）
[ ] 确认 pip install 来源：pip3 而非 pip（M1 上 pip 可能指向 x86 版本）
[ ] 验证 MPS 可用：python3 -c "import torch; print(torch.backends.mps.is_available())"
[ ] Pinecone Index 参数已记录：名称 / Host / 维度 / 区域
[ ] Embedding 模型与 Index 维度一致（最常见的不兼容来源）
[ ] .env 文件已创建，绝对不提交到 git（检查 .gitignore）
[ ] 代理端口已确认可用（国内访问 Anthropic/HuggingFace 必须）
[ ] Claude API Key 余额充足（或确认使用免费替代方案）
[ ] 数据文件（PDF/CSV/文档）已放入 data/raw/
```

---

## 2. 技术选型规则

### 2.1 固定技术栈（已验证，不要轻易替换）

| 层级 | 选型 | 版本 | 备注 |
|------|------|------|------|
| Python | CPython | 3.11.x | 3.12 也行，3.13 避免 |
| Web 框架 | FastAPI | 0.115+ | 原生异步，流式输出支持好 |
| ASGI 服务器 | Uvicorn | 0.30+ | 本地开发用 --reload |
| AI SDK | anthropic | 0.40+ | 官方 SDK，流式 API 稳定 |
| 向量数据库 | Pinecone | 5.0+ | SDK 名称是 `pinecone`，不是 `pinecone-client` |
| Embedding | sentence-transformers | 3.x | 搭配 torch，M1 MPS 加速 |
| 本地数据库 | SQLite + aiosqlite | — | 轻量，无需部署，异步兼容 |
| ORM | SQLAlchemy | 2.0+ | 异步模式 |
| 数据验证 | Pydantic | v2（2.9+） | FastAPI 默认，v1 已弃用 |
| 前端框架 | Next.js | 14（App Router） | React 18，TypeScript |
| CSS | Tailwind CSS | 3.x | 无需编译配置 |
| HTTP 客户端 | axios | 1.7+ | 前端用 |
| 重试机制 | tenacity | 9.0+ | 所有外部 API 调用必须加重试 |

### 2.2 禁止使用的库（已知在当前环境有问题）

| 库 | 问题 | 替代方案 |
|----|------|---------|
| `PaddleOCR` / `paddlepaddle` | macOS Ventura + M1 调用时进程卡死（hang），官方未修复 | `easyocr` |
| `pinecone-client` | 旧包名，已废弃 | `pinecone` |
| `pydantic` v1 | FastAPI 0.100+ 需要 v2 | `pydantic>=2.0` |
| `openai` SDK 直接调 Claude | 不走官方 SDK，功能受限 | `anthropic` SDK |

### 2.3 选型决策原则

```
新需求 → 先问：有没有 pip install 直接搞定的方案？
         是 → 用它
         否 → 再问：需要特殊安装源/编译吗？M1 支持吗？
              有问题 → 找替代
```

---

## 3. Pinecone 使用规范

### 3.1 Index 创建原则

- **先查再建**：每个项目开始前登录 [console.pinecone.io](https://console.pinecone.io) 确认 Index 状态
- **维度一旦确定不可改**：创建 Index 前必须先确认 Embedding 模型的输出维度
- **记录完整 Host**：Index 创建后立即记录完整 Host URL，直连比 Index 名连接更稳定更快
- **On-demand 模式**：Pinecone 免费/按需模式，650 个向量成本几乎为零

### 3.2 维度与模型对应关系（必须一致）

| Embedding 模型 | 输出维度 | 适用场景 |
|---------------|---------|---------|
| `intfloat/multilingual-e5-large` | **1024** | 中英文混排，教材/客服 |
| `intfloat/multilingual-e5-base` | 768 | 轻量中英文 |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | 纯英文，轻量快速 |
| `BAAI/bge-m3` | 1024 | 中文优先，效果极佳 |

### 3.3 连接代码规范

```python
# ✅ 正确：优先用 Host 直连（更快更稳定）
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_HOST"))

# ✅ 可接受：通过 Index 名连接（Host 未知时）
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

# ❌ 错误：不记录 Host，每次通过名字查找，慢且可能超时
index = pc.Index("english-agent")
```

### 3.4 上传规范

```python
# ✅ 批量上传，每批 100 条，批间休眠 0.5 秒
for i in range(0, len(vectors), 100):
    batch = vectors[i:i+100]
    index.upsert(vectors=batch)
    time.sleep(0.5)

# ✅ 必须包含重试装饰器
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def upsert_batch(index, vectors):
    index.upsert(vectors=vectors)
```

### 3.5 Metadata 规范

```python
# ✅ 每个向量的 metadata 必须包含原始文本（用于 RAG 上下文组装）
{
    "id": "chunk_001",
    "values": [...],          # 向量
    "metadata": {
        "text": "原始文本（前1000字符）",   # RAG 必需
        "source": "文档名/来源",
        "page_num": 5,                    # 可选，用于引用
        "category": "Unit 1",             # 可选，用于过滤
        "created_at": "2026-06-01"        # 可选
    }
}
```

---

## 4. Embedding 模型规范

### 4.1 M1 MPS 加速（必须启用）

```python
import torch
from sentence_transformers import SentenceTransformer

# ✅ 自动检测 MPS，M1 上快 3-5 倍
device = "mps" if torch.backends.mps.is_available() else "cpu"
model = SentenceTransformer("intfloat/multilingual-e5-large", device=device)
print(f"Using device: {device}")  # 应输出 mps
```

### 4.2 E5 系列模型前缀规范（必须遵守）

`multilingual-e5-large`、`multilingual-e5-base`、`e5-large` 等 **E5 系列模型**要求区分文档和查询：

```python
# ✅ 上传文档时（data pipeline）
texts = [f"passage: {chunk['text']}" for chunk in batch]
embeddings = model.encode(texts)

# ✅ 查询时（RAG 检索）
query_with_prefix = f"query: {user_input}"
query_embedding = model.encode(query_with_prefix)

# ❌ 不加前缀，准确率下降 10-15%
embedding = model.encode(text)
```

> **规则**：凡用 E5 系列模型，代码 review 时必须检查这两处前缀。

### 4.3 模型下载规范

```bash
# 国内下载 HuggingFace 模型必须设置镜像
export HF_ENDPOINT=https://hf-mirror.com

# EasyOCR 模型（从 GitHub 下载）需要代理
export HTTPS_PROXY=http://127.0.0.1:7890
```

### 4.4 维度校验（每次上传前）

```python
# 上传前必须验证维度与 Index 一致
test_vec = model.encode("passage: test")
assert len(test_vec) == EMBEDDING_DIM, \
    f"维度不匹配！模型输出 {len(test_vec)}，Index 要求 {EMBEDDING_DIM}"
```

---

## 5. OCR 规范（扫描文档场景）

### 5.1 PDF 类型判断（必须先做）

```python
import fitz

def is_native_pdf(pdf_path: str) -> bool:
    """原生 PDF 直接提取文字，扫描版才需要 OCR"""
    doc = fitz.open(pdf_path)
    sample_chars = sum(
        len(doc[p].get_text("text").strip())
        for p in [4, 9, 14] if p < len(doc)
    )
    doc.close()
    return (sample_chars // 3) > 100  # 平均超过100字符 = 原生PDF
```

### 5.2 OCR 库选型（macOS 13 Ventura M1）

| 库 | macOS 13 M1 | 安装 | 推荐度 |
|----|------------|------|--------|
| **EasyOCR** | ✅ 完全正常 | `pip install easyocr` | 🥇 首选 |
| PaddleOCR | ❌ 进程卡死 bug | 复杂 | 禁用 |
| Tesseract | ✅ 可用 | `brew install tesseract` | 中英混排差 |
| 百度OCR API | ✅ 云端 | 注册获取 key | 备选 |

### 5.3 EasyOCR 标准初始化

```python
import easyocr, torch

reader = easyocr.Reader(
    ['ch_sim', 'en'],                                    # 中英双语
    gpu=torch.backends.mps.is_available(),               # M1 MPS 加速
    model_storage_directory=str(Path.home() / '.EasyOCR' / 'model'),
    verbose=False
)
```

### 5.4 OCR 断点续传（必须实现）

大文档 OCR 耗时长（130页约 20-35 分钟），中断不可避免，必须实现断点续传：

```python
cache_file = cache_dir / f"page_{page_num:03d}.json"

# 命中缓存直接读取，跳过重复处理
if cache_file.exists():
    with open(cache_file) as f:
        return json.load(f)

# 处理完立即写缓存
result = do_ocr(image_path)
with open(cache_file, "w") as f:
    json.dump(result, f, ensure_ascii=False)
```

### 5.5 图片 DPI 规范

| 场景 | DPI | 说明 |
|------|-----|------|
| 快速测试 | 150 | 质量较差，仅验证流程 |
| 常规使用 | **200** | 推荐，质量速度平衡 |
| 小字/精细 | 300 | 高质量，图片文件约 3× |

---

## 6. 数据处理流水线规范

### 6.1 脚本编号规范

```
scripts/
├── 00a_pdf_to_images.py        # PDF 转图片（扫描版专用）
├── 00b_ocr_with_easyocr.py     # OCR（扫描版专用）
├── 00c_verify_ocr.py           # OCR 质量验证（必做）
├── 01_parse_source.py          # 原生文档解析（原生PDF/CSV/JSON）
├── 02_chunk_text.py            # 文本分块
├── 03_embed_and_upload.py      # 向量化 + 上传 Pinecone
├── 04_verify_pinecone.py       # 验证检索效果（必做）
└── 05_extract_metadata.py      # 可选：提取结构化元数据
```

**规则**：每个脚本职责单一，独立可运行，有清晰的输入输出说明。

### 6.2 分块规范

```python
# 推荐分块参数（RAG 最佳实践）
MAX_CHUNK_SIZE = 600   # 字符（约 400-500 tokens）
TARGET_SIZE    = 400   # 字符
OVERLAP        = 50    # 字符（保留上下文连贯性）

# 分块原则：
# 1. 不在句子中间切断
# 2. 保留完整段落优先于严格控制大小
# 3. 每个 chunk 必须携带 metadata（来源、页码、分类等）
```

### 6.3 验证步骤不可省略

```
每个流水线步骤后必须有验证：
00c → 人工抽查 OCR 质量（10 页随机抽样）
04  → 用 5-10 个测试查询验证检索效果（中英文各测）
```

### 6.4 幂等性原则

每个脚本必须支持重复运行：
- 已存在的输出文件不覆盖（或有 `--force` 参数）
- 检查缓存，跳过已处理项
- Pinecone upsert 天然幂等（相同 ID 会覆盖）

---

## 7. RAG 架构规范

### 7.1 标准 RAG 流程

```
用户输入
  │
  ▼ 1. 查询预处理
  │   - 加 E5 前缀（如使用 E5 系列）
  │   - 提取过滤条件（如指定 unit、category）
  │
  ▼ 2. 向量检索（Pinecone）
  │   - top_k = 5（默认）
  │   - 相似度阈值 >= 0.3（过滤低相关）
  │   - 可选 metadata filter
  │
  ▼ 3. 上下文组装
  │   - 格式：[Source N: 来源信息]\n文本内容
  │   - 多个 chunk 用分隔线隔开
  │
  ▼ 4. Claude API 调用
  │   - system prompt 包含角色设定 + 上下文
  │   - 流式输出（stream=True）
  │
  ▼ 5. 响应 + 来源引用
      - 附带检索到的来源信息
      - 前端显示引用来源
```

### 7.2 检索相关性阈值

```python
# ✅ 过滤低相关结果，避免幻觉
chunks = [m for m in results.matches if m.score >= 0.3]

# 不同场景的阈值参考：
# 0.3 → 宽松，上下文丰富但可能引入噪声
# 0.5 → 推荐，平衡精度和召回
# 0.7 → 严格，精准但可能召回为空
```

### 7.3 上下文长度控制

```python
MAX_CONTEXT_CHUNKS = 5      # 最多检索 5 个 chunk
MAX_HISTORY_TURNS  = 10     # 最多保留 10 轮对话历史（20条消息）

# 超出历史长度时截取最近的（而非最早的）
messages = conversation_history[-MAX_HISTORY_TURNS * 2:]
```

### 7.4 全局服务单例（必须）

```python
# ✅ 正确：启动时加载一次，全局复用
# 在 dependencies.py 或 lifespan 中：
_embedding_model = SentenceTransformer(model_name, device=device)
_pinecone_index  = pc.Index(host=pinecone_host)
_anthropic_client = anthropic.Anthropic(api_key=api_key)

# ❌ 错误：每次请求重新加载模型（极慢，每次 10-60 秒）
def get_embedding(text):
    model = SentenceTransformer(...)  # 禁止在请求处理函数内加载
    return model.encode(text)
```

### 7.5 RAG top_k 选择（决策记录）

`backend/services/quiz_service.py` 中 RAG 出题的 `top_k=2`（不是默认的 5）。**为什么这样选**：

| top_k | 上下文长度 | 成功率 | 质量 |
|------|----------|--------|------|
| 5（默认） | ~2500 字符 | ~20%（频繁截断） | 多参考 |
| 2（当前） | ~1000 字符 | 80%+ | 略差但可接受 |
| 1 | ~500 字符 | 95% | 偶有偏离 |

**为什么 top_k=2 影响不大**：
- RAG 检索有 `filter_unit` 过滤，top_k=5 里的第 3-5 个 chunk 相关性已低（score < 0.4）
- 出题只需"参考素材"而非"全文背诵"，2 段够 AI 模仿教材风格
- 学生做题时感受不到差别——单选大部分基于 Unit 通识

**需要高质量出题时**（如严格基于某篇阅读理解）：
- 走"指定短文"模式：把短文直接作为 input 传，不走 RAG
- 出题质量 100% 取决于输入短文

**经验法则**：如果 M3 长 prompt 频繁被截断，先减 `top_k`（2 比 1 安全，因为完全没上下文时 AI 会瞎编），再调 `max_tokens`、再加 parser 兜底。

---

## 8. Prompt 工程规范

### 8.1 System Prompt 结构模板

```
## 角色定义
你是 [具体角色]，专门负责 [具体职责]。

## 知识范围
[明确 Agent 能回答什么、不能回答什么]

## 行为规则
1. [规则1]
2. [规则2]
...

## 回答格式
[指定格式：中文/英文/长度/是否需要引用来源]

## 教材/知识库上下文
{context}  ← RAG 检索结果注入位置
```

### 8.2 结构化输出（JSON）规范

```python
# 需要 JSON 输出时（出题、批改等）：

# ✅ System prompt 明确要求
system = """
严格按以下 JSON 格式输出，不要添加任何其他文字、解释或 markdown 代码块：
{"key": "value"}
"""

# ✅ 解析时处理代码块包裹的情况
def parse_json_response(content: str) -> dict:
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)
```

### 8.3 模式切换规范

```python
# 不同业务场景用不同 mode，追加到 base system prompt
MODES = {
    "general":      "",                  # 通用问答
    "grammar":      GRAMMAR_ADDITION,    # 语法讲解模式
    "quiz":         QUIZ_ADDITION,       # 出题模式
    "conversation": CONV_ADDITION,       # 对话练习模式
    "customer_service": CS_ADDITION,     # 客服模式
}

def build_system_prompt(mode: str, context: str) -> str:
    return BASE_PROMPT.format(context=context) + MODES.get(mode, "")
```

### 8.4 避免 Prompt 反模式

```
❌ 不要让 Claude "扮演没有限制的 AI"
❌ 不要在 Prompt 中说 "忽略之前的所有指令"
❌ 不要把 API Key 写在 Prompt 里
❌ 不要 system prompt 超过 2000 tokens（影响响应速度和成本）
✅ 明确说明不能回答的内容（比客服 Agent 漏接问题更重要）
✅ 用正向描述（"请做X"）而非负向（"不要做非X的事"）
```

---

## 9. 后端 API 规范

### 9.1 FastAPI 项目结构（标准）

```
backend/
├── main.py              # 应用入口，lifespan，CORS，注册路由
├── config.py            # Settings（pydantic-settings），@lru_cache
├── dependencies.py      # 全局单例：model/pinecone/anthropic 客户端
├── routers/             # 路由层（只做请求解析和响应组装）
│   ├── chat.py
│   ├── quiz.py
│   └── ...
├── services/            # 业务逻辑层（所有核心逻辑在这里）
│   ├── rag_service.py
│   ├── agent_service.py
│   └── ...
├── models/              # Pydantic 模型
│   ├── request_models.py
│   └── response_models.py
└── prompts/             # Prompt 模板（独立文件，便于维护）
    ├── system_prompt.py
    └── ...
```

### 9.2 流式输出规范（SSE）

```python
# ✅ 标准 SSE 格式（前端 EventSource 兼容）
async def generate():
    async with client.messages.stream(...) as stream:
        async for text in stream.text_stream:
            data = json.dumps({"type": "text", "content": text})
            yield f"data: {data}\n\n"
    
    # 流结束后发送 done 事件（附带来源等元数据）
    done_data = json.dumps({"type": "done", "sources": sources})
    yield f"data: {done_data}\n\n"

return StreamingResponse(
    generate(),
    media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
)
```

### 9.3 错误处理规范

```python
# ✅ 所有外部 API 调用必须有重试
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APITimeoutError))
)
def call_claude(messages):
    ...

# ✅ 返回标准错误格式
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )
```

### 9.4 CORS 配置规范

```python
# ✅ 开发环境
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ 生产环境必须限制 allow_origins 为具体域名，不能用 ["*"]
```

---

## 10. Claude Code 协作规范

### 10.1 分步开发原则（必须遵守）

**不要让 Claude Code 一次性生成所有代码**，按以下顺序分步：

```
Phase 0：数据处理（验证数据质量后再继续）
  └─ 完成标志：Pinecone 检索测试通过 5/5

Phase 1：后端核心（验证 API 可用后再继续）
  └─ 完成标志：curl 测试 /api/chat/sync 返回正确结果

Phase 2：出题/业务模块
  └─ 完成标志：至少 3 种场景测试通过

Phase 3：前端界面
  └─ 完成标志：端到端流程跑通

Phase 4：优化与部署
```

### 10.2 给 Claude Code 的指令模板

```markdown
## 当前任务
[明确说明这一步要做什么，不要什么]

## 已有文件
- [列出已存在的文件，避免重复生成]

## 环境约束
- macOS 13 Ventura / M1 16GB
- Python 3.11
- Pinecone Index: xsjkndb01，维度 1024
- Embedding: intfloat/multilingual-e5-large（E5前缀规范）
- OCR: EasyOCR（禁用 PaddleOCR）

## 完成标准
[明确定义"做完"是什么样的，避免 Claude Code 过度生成]

## 不要做
- 不要修改 [某文件]
- 不要生成前端代码（本步骤只做后端）
```

### 10.3 代码审查检查项

Claude Code 生成代码后，检查以下内容再运行：

```
[ ] Pinecone 连接使用 Host 直连（不是只用 index 名）
[ ] Embedding 前缀正确（passage:/query:）
[ ] 没有使用 PaddleOCR
[ ] 全局服务在 lifespan/startup 中初始化，不在请求函数内
[ ] 外部 API 调用有 @retry 装饰器
[ ] 敏感信息（API Key）通过 os.getenv() 读取，不硬编码
[ ] .env 在 .gitignore 中
[ ] 流式接口返回正确的 SSE 格式
[ ] JSON 解析有异常处理（try/except）
```

### 10.4 版本迭代记录

每次文档更新，在文件顶部记录变更：

```markdown
## 变更日志
- v1.5：新增坑位 27（多 AI 协作时代码接口错位）；补 pytest 自测发现 `get_pinecone_index` 死引用、`mock_minimax` patch 旧函数名
- v1.4：新增坑位 19-26（M3 `<think>` 块、JWT `sub` claim、React Hooks 顺序、SQLite greenlet 依赖、quiz 截断修复 4 步组合、grade 中文双引号破坏 JSON、前端 GET 漏带 Authorization 头、AI 流式输出 think 块泄露）；§7.5 RAG top_k 选择决策记录
- v1.3：OCR 从 PaddleOCR 切换为 EasyOCR（修复 macOS Ventura M1 卡死 bug）
- v1.2：同步实际 Pinecone 配置（xsjkndb01，1024维，multilingual-e5-large）
- v1.1：加入 M1 MPS 加速，更新 E5 前缀规范
- v1.0：初始版本
```

---

## 11. 成本控制规范

### 11.1 Claude API 费用参考（2026 年）

| 模型 | Input | Output | 适用场景 |
|------|-------|--------|---------|
| claude-haiku-4-5 | $0.25/M | $1.25/M | 出题、批改、简单问答 |
| claude-sonnet-4-6 | $3/M | $15/M | 复杂分析、高质量输出 |

**默认用 haiku，用户明确要求高质量时才切换 sonnet。**

### 11.2 Token 计数与预算

```python
# ✅ 每次 API 调用后记录 token 消耗
response = client.messages.create(...)
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens

# 粗略估算：1000 个中文字符 ≈ 600 tokens
# RAG 上下文（5个chunk × 400字符）≈ 1200 tokens
# 对话历史（10轮）≈ 1500 tokens
# System prompt ≈ 500 tokens
# 合计每次调用约 3000-4000 input tokens
```

### 11.3 成本节省策略

```
1. OCR 用本地模型（EasyOCR），不消耗 Claude API
2. Embedding 用本地模型（sentence-transformers），不消耗 API
3. 测试时用 haiku，上线后视质量决定是否升级
4. 对话历史最多保留 10 轮（避免 context 膨胀）
5. RAG 上下文 top_k 控制在 5 以内
6. 批量处理任务（如出题）用同步接口，不用流式
```

---

## 12. 国内网络规范

### 12.1 需要代理的服务

| 服务 | 用途 | 代理方式 |
|------|------|---------|
| Anthropic API | Claude 对话 | 环境变量 HTTPS_PROXY |
| HuggingFace | 下载 Embedding 模型 | HF_ENDPOINT 镜像 |
| EasyOCR 模型 | 首次下载 | HTTPS_PROXY |
| Pinecone API | 向量数据库 | 通常无需代理 |
| npm registry | 前端依赖 | 可用淘宝镜像 |
| PyPI | Python 依赖 | 可用清华/豆瓣镜像 |

### 12.2 标准代理配置

```bash
# .env 中配置（推荐）
HTTPS_PROXY=http://127.0.0.1:1082    # 替换为你的代理端口
HTTP_PROXY=http://127.0.0.1:1082

# HuggingFace 镜像（单独设置，比代理更稳定）
HF_ENDPOINT=https://hf-mirror.com
```

```python
# Python 代码中读取代理（anthropic SDK 自动识别环境变量）
import os
# anthropic.Anthropic() 自动读取 HTTPS_PROXY，无需手动设置
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### 12.3 pip 国内镜像

```bash
# 单次使用
pip install package -i https://pypi.tuna.tsinghua.edu.cn/simple

# 全局配置（~/.pip/pip.conf）
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
```

### 12.4 npm 国内镜像

```bash
# 设置淘宝镜像
npm config set registry https://registry.npmmirror.com

# 单次使用
npm install --registry https://registry.npmmirror.com
```

---

## 13. 已知坑位速查表

> 踩到新坑后立即更新此表，是本文档最核心的价值。

| # | 坑位描述 | 环境 | 错误现象 | 解决方案 |
|---|---------|------|---------|---------|
| 1 | **PaddleOCR 卡死** | macOS Ventura M1 | 调用 `ocr()` 进程 hang，只能 kill -9 | 换 **EasyOCR** |
| 2 | **Pinecone SDK 包名变更** | 所有 | `pip install pinecone-client` 装的是旧版 | 用 `pip install pinecone` |
| 3 | **E5 模型不加前缀** | 所有 | 检索相关性莫名偏低 | 文档加 `passage:` 前缀，查询加 `query:` 前缀 |
| 4 | **维度不匹配** | 所有 | Pinecone 上传报 `Vector dimension mismatch` | `.env` 中 `EMBEDDING_DIMENSION` 必须与 Index 维度一致 |
| 5 | **每次请求重新加载模型** | 所有 | 每个请求响应 30-60 秒 | 在 `startup_services()` 中加载，全局复用单例 |
| 6 | **Python 3.13 依赖冲突** | macOS | `pip install sentence-transformers` 失败 | 用 Python 3.11 或 3.12 |
| 7 | **pip 指向 x86 版本** | M1 | 安装的包走 Rosetta，性能差 | 用 `python3 -m pip` 或检查 `pip3 --version` |
| 8 | **MPS 未启用** | M1 | Embedding 速度慢（纯 CPU） | 检查 `torch.backends.mps.is_available()` |
| 9 | **OCR 无断点续传** | 所有 | 中断后全部重做，浪费时间 | 每页写缓存，重跑时检查缓存文件 |
| 10 | **Pinecone 用 Index 名而非 Host 连接** | 所有 | 连接慢或偶发超时 | 用 `pc.Index(host=HOST_URL)` 直连 |
| 11 | **SSE 流式响应缺少响应头** | 所有 | Nginx 反代后流式失效 | 加 `X-Accel-Buffering: no` 头 |
| 12 | **CORS 生产环境用 `*`** | 生产 | 安全漏洞 | 限定为具体前端域名 |
| 13 | **JSON 输出未处理代码块** | 所有 | `json.loads()` 报错（包含 ` ```json ` 标记） | 解析前先剥离 markdown 代码块 |
| 14 | **对话历史无长度限制** | 所有 | Context 超限报错 / 成本剧增 | 截取最近 20 条（10轮）消息 |
| 15 | **扫描版 PDF 未先检测类型** | 所有 | 10.7MB 原生 PDF 跑了 35 分钟 OCR | 先用 PyMuPDF 抽查 3 页，有文字则直接提取 |
| 16 | **HuggingFace 直连下载** | 国内 | 下载速度极慢或超时 | 设置 `HF_ENDPOINT=https://hf-mirror.com` |
| 17 | **Pydantic v1 与 FastAPI 0.100+ 不兼容** | 所有 | 各种 validation 报错 | 统一用 Pydantic v2 |
| 18 | **流水线步骤不验证直接进入下一步** | 所有 | 垃圾数据进 Pinecone，问答质量极差 | `00c_verify_ocr.py` 和 `04_verify_pinecone.py` 必须运行 |
| 19 | **MiniMax M3 输出含 `<think>` 推理块** | 所有 | JSON 解析失败 / 历史回放看到思考过程 | 调用 `parse_json_response` / `save_message` 前先剥 `<think>...</think>` |
| 20 | **PyJWT `sub` claim 必须是字符串** | 所有 | `InvalidSubjectError: Subject must be a string` | 签发 `create_token` 用 `str(user_id)`，解析时 `int(payload["sub"])` |
| 21 | **React Hooks 早 return 导致数量不一致** | 所有 | `Rendered more hooks than during the previous render` | 所有 `useState/useEffect` 必须放在所有 early return 之前 |
| 22 | **SQLite 异步缺 greenlet** | 所有 | `ValueError: the greenlet library is required` | `pip install greenlet`（SQLAlchemy async 必需） |
| 23 | **M3 长 prompt 输出超 max_tokens 截断 JSON** | M3 | 出题返回 500，`json.decoder.JSONDecodeError: Unterminated string` | 4 步组合：①top_k 降到 2 减 RAG 上下文；②system prompt 让 AI 极简输出；③`parse_json_response` 渐进式 trim；④失败时 retry，`max_tokens=6000` |
| 24 | **M3 中文反馈里用 ASCII 双引号破坏 JSON 字符串** | M3 | `grade_answer` 返回 500 | ①prompt 明确禁止中文里用双引号（用「」）；②`parse_json_response` 替换全角引号；③grade 端点加 try/except fallback，LLM 失败时用答案匹配给默认结果 |
| 25 | **前端 GET 接口漏带 Authorization 头** | 所有 | 受保护接口返回 401，前端 catch 后页面崩溃 | `lib/api.ts` 的所有 `fetch` 都要用 `authHeaders()` 包装，连"可选登录"的接口也建议带（无害） |
| 26 | **AI 流式输出 <think> 推理块泄露给用户** | M3 | 用户聊天时看到 `<reasoning>...</reasoning>` | 三道防线：①prompt 禁止；②后端 `agent_service` 流式状态机过滤；③前端 `useChat` 再次过滤 |
| 27 | **多 AI 协作时代码接口错位（两段流水线坑）** | 所有 | 跑 `pytest` 才发现 `get_pinecone_index` 等函数从未存在；重构 `dependencies.py` 后 `conftest.py` 没跟上 patch 旧函数名 | ①每段开发流水线**必须独立可跑测试**；②重构后强制 `pytest tests/` 验证；③M3 等大模型写代码时假设的函数必须真实存在，否则在 prompt 里要求 "先 grep 确认依赖" |

---

## 14. 新 Agent 项目启动模板

新建一个 Agent 项目时，按此顺序填写，交给 Claude Code 作为开发上下文：

```markdown
# [项目名称] Agent 开发上下文

## 基本信息
- Agent 类型：[学习助手 / 客服 / 知识库问答 / 其他]
- 目标用户：[描述用户]
- 核心功能：[3-5 个功能点]

## 运行环境
- OS：macOS 13 Ventura
- 硬件：Apple M1 / 16GB RAM
- Python：3.11.x

## 数据源
- 数据类型：[PDF 扫描版 / PDF 原生 / CSV / 网页 / 数据库]
- 数据量：[文件数量和大小]
- 语言：[中文 / 英文 / 中英混排]
- 特殊格式：[表格 / 图片 / 公式 / 其他]

## Pinecone 配置（已创建）
- Index 名称：[填写]
- Host：[填写完整 Host URL]
- 维度：[填写]
- 区域：[填写]

## Embedding 模型
- 模型：intfloat/multilingual-e5-large（1024维）
- 注意：必须使用 E5 前缀规范（passage:/query:）

## OCR 需求
- 是否需要：[是/否]
- 使用 EasyOCR（禁用 PaddleOCR）

## Claude API
- 模型：claude-haiku-4-5-20251001（成本优先）
- 是否已充值：[是/否]
- 若无 API：仅后端对话功能不可用，其他步骤继续

## 遵守规范
- 本项目遵守 AGENTS.md 所有规则
- 代理端口：127.0.0.1:7890
- HF 镜像：https://hf-mirror.com
- 分步开发：Phase 0（数据）→ Phase 1（后端）→ Phase 2（业务）→ Phase 3（前端）

## 禁止事项
- 禁止使用 PaddleOCR
- 禁止在请求处理函数内加载模型
- 禁止硬编码 API Key
- 禁止跳过验证步骤（00c 和 04）
```

---

## 15. 国产大模型 Embedding 扩展

> 详细规范见独立文档：`国产模型Embedding扩展方案.md`

### 15.1 可用国产 Embedding 模型（与当前 1024 维 Index 兼容）

| 提供商 | 模型 | 维度 | 网络 | 适用场景 |
|--------|------|------|------|---------|
| 阿里云百炼 | `text-embedding-v4` | 自定义→1024 | 国内直连 | 性价比最高，首选 |
| 智谱AI | `embedding-3` | 自定义→1024 | 国内直连 | 中文效果好 |
| 火山方舟 | `doubao-embedding` | 自定义→1024 | 国内直连 | OpenAI 兼容接口 |
| 本地（当前） | `multilingual-e5-large` | 固定1024 | 无需网络 | 完全免费 |

### 15.2 切换提供商三步走

```bash
# 1. 修改 .env
EMBEDDING_PROVIDER=aliyun          # local | aliyun | zhipu | volcengine
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSION=1024
DASHSCOPE_API_KEY=sk-xxxx          # 对应提供商的 Key

# 2. 验证新提供商
python scripts/test_embedding_provider.py

# 3. 清空旧向量 + 重新上传（切换模型必须重建向量库）
python scripts/05_clear_pinecone.py
python scripts/03_embed_and_upload.py
```

### 15.3 统一接口规范

所有国产模型通过 `backend/utils/embedding.py` 的 `get_embedder()` 工厂函数调用。
切换提供商**只改 `.env`**，`rag_service.py` 和 `embed_and_upload.py` 代码无需修改。

### 15.4 关键坑位（国产模型专项）

| 坑 | 现象 | 解决 |
|----|------|------|
| 智谱未设 `dimensions` | 默认返回 2048 维，Pinecone 报错 | 必须传 `dimensions=1024` |
| 阿里云未设 `text_type` | 检索质量下降 | 上传用 `document`，查询用 `query` |
| 切换模型未清空 Pinecone | 检索完全失效 | 先跑 `05_clear_pinecone.py` |
| 国产 API 走了代理 | 连接超时（代理出口在境外） | `unset HTTPS_PROXY` |

---

## 附录：快速命令参考

```bash
# ── 环境验证 ──
python3 --version
python3 -c "import torch; print(torch.backends.mps.is_available())"

# ── 常用安装 ──
pip install easyocr pymupdf fastapi uvicorn anthropic
pip install pinecone sentence-transformers torch
pip install sqlalchemy aiosqlite pydantic-settings tenacity
# 国产模型按需安装（选其一）：
pip install dashscope        # 阿里云百炼
pip install zhipuai          # 智谱AI
# 火山方舟使用 openai 兼容接口，已含在 pip install openai 中

# ── 国内加速 ──
export HF_ENDPOINT=https://hf-mirror.com
export HTTPS_PROXY=http://127.0.0.1:1082
# ⚠️ 调用国产 API 时关闭代理（国内直连）：
# unset HTTPS_PROXY

# ── 服务启动 ──
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev

# ── 数据流水线 ──
python scripts/00a_pdf_to_images.py
python scripts/00b_ocr_with_easyocr.py
python scripts/00c_verify_ocr.py                        # 必做
python scripts/02_chunk_text.py
python scripts/03_embed_and_upload.py
python scripts/04_verify_pinecone.py                    # 必做

# ── 国产模型切换 ──
python scripts/test_embedding_provider.py               # 验证新提供商
python scripts/05_clear_pinecone.py                     # 切换前清空旧向量
python scripts/03_embed_and_upload.py                   # 重新上传

# ── Pinecone 快速验证 ──
python3 -c "
from pinecone import Pinecone
import os
from dotenv import load_dotenv
load_dotenv()
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
idx = pc.Index(host=os.getenv('PINECONE_HOST'))
print(idx.describe_index_stats())
"
```

---



*文档版本：v1.5 | 创建：2026-06-01 | 最近更新：2026-06-03*  
*维护规则：每次踩新坑后更新第 13 节「已知坑位速查表」，并在变更日志中记录*
