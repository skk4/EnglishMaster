# EnglishMaster Agent — 测试计划

> **目标读者**：开发工程师、QA、AI 工程师、运维
> **状态**：v1.0（待评审）
> **更新原则**：每修复一个 bug 加 1 个回归测试；每加 1 个 Phase 补对应维度的测试点

---

## 目录

1. [总览与测试金字塔](#1-总览与测试金字塔)
2. [功能测试 — 后端 API](#2-功能测试--后端-api)
3. [功能测试 — 前端 UI](#3-功能测试--前端-ui)
4. [数据流水线测试](#4-数据流水线测试)
5. [性能测试](#5-性能测试)
6. [AI 模型效果评估](#6-ai-模型效果评估)
7. [AI 模型微调计划](#7-ai-模型微调计划)
8. [Harness / 自动化测试基础设施](#8-harness--自动化测试基础设施)
9. [质量门禁与发布标准](#9-质量门禁与发布标准)
10. [风险评估与缓解](#10-风险评估与缓解)

---

## 1. 总览与测试金字塔

### 1.1 测试目标

| 目标 | 衡量 |
|------|------|
| **正确性**：所有功能按规格工作 | 0 个 P0 bug 进入生产 |
| **稳定性**：不出现回归 | 老功能不被新代码破坏 |
| **性能**：响应在用户可接受范围 | P95 聊天 ≤ 8s、出题 ≤ 15s |
| **AI 质量**：RAG 检索准、回答有用、出题合理 | recall@5 ≥ 0.85、批改准确率 ≥ 90% |
| **可维护性**：新功能/修 bug 有自动化测试保护 | 覆盖率 ≥ 70% |
| **可观测**：测试结果清晰可读 | CI 报告含覆盖率/性能趋势 |

### 1.2 七个测试维度

| # | 维度 | 主要工具 | 谁负责 | 频率 |
|---|------|---------|--------|------|
| 2 | **后端功能测试** | pytest + httpx AsyncClient | 后端开发 | 每个 PR |
| 3 | **前端功能测试** | Jest + React Testing Library | 前端开发 | 每个 PR |
| 4 | **数据流水线测试** | pytest + 文件系统断言 | 数据工程 | OCR/分块脚本改时 |
| 5 | **性能测试** | locust / k6 / wrk + 监控面板 | 全栈 | 版本发布前 |
| 6 | **AI 模型效果评估** | 自建评估脚本 + 人评 | AI 工程师 | 模型切换/微调前 |
| 7 | **AI 模型微调** | 训练脚本 + 评估 | AI 工程师 | 不定期 |
| 8 | **Harness / 自动化** | GitHub Actions + Pytest + Playwright | DevOps | 持续 |

### 1.3 测试金字塔

```
           /\
          /  \          E2E (Playwright) ~5%
         /────\         跨页面流：注册→对话→出题→批改→看进度
        /      \        
       /────────\       集成测试 (pytest + httpx) ~25%
      /          \      端到端 API：每个接口的请求-响应
     /────────────\     
    /              \   单元测试 (pytest) ~70%
   /                  \ 纯函数：parse_json_response / 分块 / auth
  ────────────────────
```

**比例原则**：
- 70% 单元测试（快、稳定、低耦合）
- 25% 集成测试（API 协议、数据流）
- 5% E2E（最慢但最贴近用户）

### 1.4 测试环境

| 环境 | 用途 | 数据 |
|------|------|------|
| **unit** | 单测，跑本地 | mock 一切外部依赖 |
| **integration** | API 集成 | 真 Pinecone + Mock MiniMax（或真，但录 response） |
| **staging** | 完整 E2E | 真 Pinecone + 真 MiniMax + 真 SQLite + 真用户 |
| **production** | 监控、抽样回归 | 同 staging |

### 1.5 不在测试范围内的

- 部署脚本（Railway/Vercel 部署走手动 + smoke test）
- 前端 SSR 性能（P95 渲染时间）— 阶段 1 数据量小，无需关注
- 浏览器兼容性（默认只测最新版 Chrome + Safari）
- 网络抖动（用 retry + 监控，不在单测模拟）

---

## 2. 功能测试 — 后端 API

### 2.1 测试方法

- **框架**：pytest 8.3 + pytest-asyncio
- **HTTP 客户端**：httpx AsyncClient + ASGITransport（无需启动真服务器）
- **Mock**：MiniMax M3 客户端、Pinecone 连接、文件 I/O
- **数据库**：每个测试用独立临时 SQLite（fixture）

### 2.2 文件结构

```
tests/
├── conftest.py                  # 全局 fixture
├── test_auth.py                 # /api/auth/*
├── test_chat.py                 # /api/chat/*
├── test_history.py              # /api/history/*
├── test_quiz.py                 # /api/quiz/*
├── test_progress.py             # /api/progress/*
├── test_vocabulary.py           # /api/vocab/*
├── test_health.py               # /api/health
└── helpers/
    ├── mock_minimax.py          # 录制/回放 M3 response
    └── mock_pinecone.py
```

### 2.3 `/api/auth/*` 测试矩阵

| 编号 | 场景 | 输入 | 预期 | 备注 |
|------|------|------|------|------|
| AUTH-01 | 正常注册 | username="alice", password="pw1234" | 200, 返回 token | |
| AUTH-02 | 注册：用户名 < 3 字符 | username="ab" | 400 "用户名至少 3 位" | |
| AUTH-03 | 注册：密码 < 4 字符 | password="ab" | 400 "密码至少 4 位" | |
| AUTH-04 | 注册：用户名已存在 | alice 重复注册 | 400 "用户名已存在" | |
| AUTH-05 | 正常登录 | alice + 正确密码 | 200, token | |
| AUTH-06 | 登录：错密码 | alice + 错密码 | 401 | |
| AUTH-07 | 登录：不存在的用户 | unknown user | 401（不暴露用户是否存在） | |
| AUTH-08 | /me 无 token | 无 Authorization 头 | 401 | |
| AUTH-09 | /me 假 token | Bearer "fake.jwt.token" | 401 | |
| AUTH-10 | /me token 过期 | 构造已过期的 token | 401 | |
| AUTH-11 | /me 正常 | valid token | 200, user 信息 | |

### 2.4 `/api/chat/*` 测试矩阵

| 编号 | 场景 | 预期 |
|------|------|------|
| CHAT-01 | sync：mock M3 返回固定文本 | 200, content + sources 正确解析 |
| CHAT-02 | sync：M3 返回 `<think>` 块 | content 不含 `<think>` |
| CHAT-03 | sync：M3 返回截断 JSON | 5 次至少 4 次成功（用 §23 fix） |
| CHAT-04 | sync：用户消息和 AI 消息都保存到 chat_messages | DB 2 条记录，mode 字段正确 |
| CHAT-05 | sync：传 session_id 时复用 | 新 user/assistant 都关联到该 session |
| CHAT-06 | sync：不传 session_id | 自动建新 session，title=首条 user |
| CHAT-07 | stream：流式 chunk 顺序 | SSE 事件顺序：text → text → done |
| CHAT-08 | stream：done 事件含 sources 和 session_id | 校验 done 事件 payload |
| CHAT-09 | 流式连接断开 | user 端不会 500（要么已存要么异常） |
| CHAT-10 | 对话历史超 20 条 | 只截取最近 20 条给 LLM |
| CHAT-11 | filter_unit/semester 透传到 RAG | mock RAGService 验证参数 |
| CHAT-12 | mode=grammar/conversation/quiz/general | 4 个 system prompt 不同 |

### 2.5 `/api/history/*` 测试矩阵

| 编号 | 场景 | 预期 |
|------|------|------|
| HIST-01 | list_sessions 空 | 返回 `[]` |
| HIST-02 | list_sessions 3 个 | 按 updated_at 倒序 |
| HIST-03 | create_session | 返回新 id |
| HIST-04 | get_session 自己的 | 返回完整 messages |
| HIST-05 | get_session 别人的 session | 404（防越权） |
| HIST-06 | delete_session 自己的 | ok |
| HIST-07 | delete_session 别人的 | 404 |
| HIST-08 | 删除 session 级联删除 messages | DB 验证 cascade |

### 2.6 `/api/quiz/*` 测试矩阵

| 编号 | 场景 | 预期 |
|------|------|------|
| QUIZ-01 | generate：unit 不存在 | 可能 RAG 返回空，AI 仍尝试出题（验证不崩） |
| QUIZ-02 | generate：count=0 | 400 |
| QUIZ-03 | generate：count=20 | 200 |
| QUIZ-04 | generate：count=21 | 400 |
| QUIZ-05 | generate：quiz_type="invalid" | 400 |
| QUIZ-06 | generate：mock 完整 M3 JSON | 200, questions 数组 |
| QUIZ-07 | generate：mock 截断 M3 JSON | 200（retry 生效） |
| QUIZ-08 | generate：M3 全失败 | 500（预期：保留 retry 后再 fail） |
| QUIZ-09 | grade：多选题答对 | score=1.0, fast path |
| QUIZ-10 | grade：多选题答错 | 调 LLM（mock） |
| QUIZ-11 | grade：填空题答对 | 调 LLM |
| QUIZ-12 | grade：空答案 | score=0.0, feedback="未作答" |
| QUIZ-13 | grade：M3 输出损坏 | 走 fallback（不 500） |
| QUIZ-14 | grade：保存到 quiz_records | 1 条新记录，user_id 正确 |

### 2.7 `/api/progress/*` 测试矩阵

| 编号 | 场景 | 预期 |
|------|------|------|
| PROG-01 | summary：0 条记录 | total=0, weak_units=[] |
| PROG-02 | summary：3 对 1 错（3 个 unit） | accuracy=0.75, weak_units 按正确率排序 |
| PROG-03 | records：分页 | limit=10 返回 ≤ 10 条 |
| PROG-04 | records：跨用户隔离 | bob 看不到 alice 的 |
| PROG-05 | vocab 更新：mastered=true | mastery_level + 1 |
| PROG-06 | vocab 更新：mastered=false | mastery_level - 1 |
| PROG-07 | vocab 更新：边界 0 → -1 | 不变 0 |
| PROG-08 | vocab 更新：边界 3 → 4 | 不变 3 |

### 2.8 `/api/vocab/*` 测试矩阵

| 编号 | 场景 | 预期 |
|------|------|------|
| VOCAB-01 | units 列表 | 返回 sem1/sem2 所有 unit |
| VOCAB-02 | unit 词汇为空 unit | 返回 `[]` |
| VOCAB-03 | unit 词汇 20 个 | 返回 ≤ 20 |
| VOCAB-04 | practice n=10 | 返回 ≤ 10 |
| VOCAB-05 | practice n=100 但总共 5 | 返回 5 |

### 2.9 `/api/health` 测试

| 编号 | 场景 | 预期 |
|------|------|------|
| HLTH-01 | GET / | 200 {"status":"ok", "model":"MiniMax-M3"} |

### 2.10 跨接口测试

| 编号 | 场景 | 目的 |
|------|------|------|
| INT-01 | 注册→登录→/me 完整流 | 验证 token 流转 |
| INT-02 | 注册 A→注册 B→A 做 2 题→B 做 1 题→/summary | 验证多用户隔离 |
| INT-03 | 注册 A→发消息→/history/sessions→再发同 session | 验证 session 复用 |
| INT-04 | CASCADE 删 user | quiz_records/vocab_progress/chat_* 全删 |

### 2.11 pytest 示例

```python
# tests/test_chat.py
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_chat_sync_strips_think_block(async_client: AsyncClient, stan_token: str):
    with patch("backend.services.agent_service.AgentService.chat_sync") as mock:
        mock.return_value = {
            "content": "<think>reasoning</think>actual answer",
            "sources": [{"unit":"Unit 1","section":"A","page_num":1,"semester":1,"score":0.9}],
        }
        resp = await async_client.post(
            "/api/chat/sync",
            headers={"Authorization": f"Bearer {stan_token}"},
            json={"message": "什么是过去时", "mode": "grammar"},
        )
    assert resp.status_code == 200
    assert "<think>" not in resp.json()["content"]
    assert "actual answer" in resp.json()["content"]
```

---

## 3. 功能测试 — 前端 UI

### 3.1 测试方法

- **框架**：Jest 29 + React Testing Library 16
- **Mock**：next/router、useAuth、API 客户端（用 MSW 拦截 fetch）
- **DOM 断言**：用户能看到什么、不能看到什么、可交互性
- **不测**样式像素（用 snapshot 仅作辅助），以语义/角色为主

### 3.2 文件结构

```
frontend/
├── lib/__tests__/                 # lib 工具测试
│   ├── auth.test.ts
│   └── api.test.ts
├── hooks/__tests__/
│   ├── useAuth.test.ts
│   └── useChat.test.ts
├── components/
│   ├── chat/__tests__/
│   │   ├── MessageBubble.test.tsx
│   │   ├── SourcePanel.test.tsx
│   │   └── InputBar.test.tsx
│   └── quiz/__tests__/
│       └── QuizCard.test.tsx
└── app/
    ├── __tests__/                 # 页面集成
    │   ├── login.test.tsx
    │   ├── chat.test.tsx          # 跑 / 但 mock useAuth
    │   ├── quiz.test.tsx
    │   ├── vocabulary.test.tsx
    │   └── progress.test.tsx
```

### 3.3 登录页 `/login`

| 编号 | 测试点 |
|------|------|
| LOGIN-01 | 渲染：登录 Tab、注册 Tab、用户名、密码、按钮 |
| LOGIN-02 | 切到注册：多出"昵称"输入框 |
| LOGIN-03 | 用户名 < 3 字符时点击注册，HTML5 required 不让提交 |
| LOGIN-04 | 错密码登录，错误提示"用户名或密码错误" |
| LOGIN-05 | 成功登录，token 存 localStorage，跳到 `/` |
| LOGIN-06 | 已登录态访问 /login 不再显示（理论上 hook 还会加载，但应被 redirect） |
| LOGIN-07 | 加载中显示 Loader2 |

### 3.4 首页 `/` (聊天)

| 编号 | 测试点 |
|------|------|
| HOME-01 | 未登录 → useAuth 跳 /login |
| HOME-02 | 侧边栏显示 4 个模式选择 |
| HOME-03 | 切模式后 mode 状态更新，输入区 placeholder 文案变 |
| HOME-04 | 输入文字→点击发送→流式 text 追加到 assistant 气泡 |
| HOME-05 | 流式光标仅在 `streaming && content` 时显示 |
| HOME-06 | 完成后 sources 出现，AI 回答上方出现 mode 标签 |
| HOME-07 | 侧边栏会话列表：当前 session 高亮 |
| HOME-08 | 点击侧边栏旧 session，loadSession 加载消息 |
| HOME-09 | 点击"+"新建对话，messages 清空，sessionId=null |
| HOME-10 | 鼠标悬停 session 显示删除按钮，点击 confirm 删除 |
| HOME-11 | 退出登录：清 localStorage，跳 /login |
| HOME-12 | header 显示当前 session 标题 |

### 3.5 `/quiz` 随堂测试

| 编号 | 测试点 |
|------|------|
| QUIZ-UI-01 | 配置页：学期/单元/题型/题数/难度 5 个选择器 |
| QUIZ-UI-02 | 点击"开始测试"loading 状态显示 |
| QUIZ-UI-03 | 题目卡片：单选 4 选项、填空 textarea、翻译 textarea |
| QUIZ-UI-04 | 单选：点击选项后高亮，提交前可改 |
| QUIZ-UI-05 | 提交后正确选项绿、错误选项红、批改区域展开 |
| QUIZ-UI-06 | "重做"按钮清当前题答案，保留题号 |
| QUIZ-UI-07 | "下一题"按钮 → 切到下一题（最后一题→ 完成） |
| QUIZ-UI-08 | 完成页：总分/答对/答错三个卡片 |
| QUIZ-UI-09 | "再测一次"回到配置页 |
| QUIZ-UI-10 | 出题报错（API 500）：在配置页显示错误提示 |

### 3.6 `/vocabulary` 词汇闪卡

| 编号 | 测试点 |
|------|------|
| VOCAB-UI-01 | 上/下册切换重新加载词表 |
| VOCAB-UI-02 | 单词正面：word + 音标 + 喇叭图标 |
| VOCAB-UI-03 | 喇叭点击调 speechSynthesis（mock） |
| VOCAB-UI-04 | 点击卡片翻面显示 pos + 翻译 |
| VOCAB-UI-05 | 翻面后"认识"/"不认识"按钮出现 |
| VOCAB-UI-06 | 标记后调 updateVocabProgress（mock） |
| VOCAB-UI-07 | "换一批"重新加载 |
| VOCAB-UI-08 | 进度 "X / N" 显示正确 |

### 3.7 `/progress` 学习进度

| 编号 | 测试点 |
|------|------|
| PROG-UI-01 | 3 个统计卡片：总题数/正确率/平均分 |
| PROG-UI-02 | 薄弱单元 Top 3 列表 |
| PROG-UI-03 | 进度条按 accuracy 比例渲染 |
| PROG-UI-04 | 最近记录列表（最多 20 条） |
| PROG-UI-05 | 0 条记录时显示"还没有做题记录" |

### 3.8 跨页面通用

| 编号 | 测试点 |
|------|------|
| UX-01 | 任何页面未登录：跳 /login |
| UX-02 | 任何受保护 API 401：弹错误提示而非 500 |
| UX-03 | API 错误有 retry 提示（连接失败重试 1 次） |
| UX-04 | 长时间请求（> 10s）显示"AI 正在..."文案 |

### 3.9 组件层测试示例

```tsx
// components/chat/__tests__/InputBar.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { InputBar } from "../InputBar";

it("calls onSend with trimmed text on Enter", () => {
  const onSend = jest.fn();
  render(<InputBar onSend={onSend} />);
  const textarea = screen.getByRole("textbox");
  fireEvent.change(textarea, { target: { value: "  hello  " } });
  fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
  expect(onSend).toHaveBeenCalledWith("hello");
});

it("does not send on Shift+Enter", () => {
  const onSend = jest.fn();
  render(<InputBar onSend={onSend} />);
  const textarea = screen.getByRole("textbox");
  fireEvent.change(textarea, { target: { value: "hello" } });
  fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
  expect(onSend).not.toHaveBeenCalled();
});
```

---

## 4. 数据流水线测试

> 6 个脚本（00a/00b/00c/02/03/04/extract_vocab）每个都有专门测试。原则：**输入 → 期望输出 → 失败模式**。

### 4.1 `00a_pdf_to_images.py` PDF 类型检测

| 编号 | 场景 | 输入 | 期望 |
|------|------|------|------|
| PIPE-01 | 原生 PDF (10.2MB 上册) | grade8_semester1.pdf | 不转图片，直接 extract text 到 raw_pages |
| PIPE-02 | 扫描版 PDF (230.6MB 下册) | grade8_semester2.pdf | 转 200 DPI PNG 到 data/images/semester2/ |
| PIPE-03 | 文件不存在 | /no/such.pdf | 优雅 skip + warning |
| PIPE-04 | 损坏的 PDF | bad.pdf | 报错但不中断整个 batch |
| PIPE-05 | 转图片断点续传 | 已存在部分图片 | 跳过已生成的页 |
| PIPE-06 | manifest.json 生成 | 任一处理 | 总数/dpi/路径正确 |

### 4.2 `00b_ocr_with_minimax.py` OCR

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-10 | 正常 OCR（132 页） | 132 个 cache + 1 个 raw_pages JSON |
| PIPE-11 | cache 命中 | 已处理的页直接读 cache，不调 M3 |
| PIPE-12 | M3 单页失败 | retry 3 次，失败记录到 errors 计数 |
| PIPE-13 | 单页 < 25 字符 | 跳过（认为是空白/插图页） |
| PIPE-14 | 章节识别：Unit 1 标题在第 5 页 | 第 5 页起 unit="Unit 1" |
| PIPE-15 | 章节识别：页码 125 误识别为 Unit 125 | 已知问题，记录在 §10 风险 |
| PIPE-16 | detect_section: "Vocabulary" 关键词 | section="Vocabulary" |
| PIPE-17 | M3 返回 `<think>` 块 | cache 中 content 不含 `<think>` |

### 4.3 `00c_verify_ocr.py` 质量验证

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-20 | sem1 1344 chars/页 avg | PASS |
| PIPE-21 | sem2 1627 chars/页 avg | PASS |
| PIPE-22 | 故意制造低质量（人为 mock avg=50） | FAIL + 列出问题 |
| PIPE-23 | 中英覆盖率 100% | PASS |
| PIPE-24 | Unit 125 警告 | 软警告，不算 hard fail |
| PIPE-25 | 跨学期：sem1 PASS, sem2 FAIL | 输出半成功状态 |

### 4.4 `02_chunk_text.py` 文本分块

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-30 | 146 页正常分块 | ~840 chunks (实测 362+479) |
| PIPE-31 | chunk_id 格式 | `s{sem}_p{page:03d}_c{idx:04d}` |
| PIPE-32 | 不在句子中间切断 | 抽查 chunk 边界是 `.!?。！？` 或换行 |
| PIPE-33 | overlap 机制 | 上一块最后一句进入下一块 |
| PIPE-34 | 已存在 output 文件 | skip（--force 才覆盖） |
| PIPE-35 | 短文本（< 100 字符） | 单 chunk 完整保留 |

### 4.5 `03_embed_and_upload.py` 向量化+上传

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-40 | 841 chunks 全上传 | Pinecone total_vector_count 增加 841 |
| PIPE-41 | 维度校验：模型输出 1024 维 | assertion 通过 |
| PIPE-42 | 批次 100，sleep 0.5s | 总时间 ≈ 4 分钟 |
| PIPE-43 | E5 prefix：chunk text 前加 "passage: " | 实际行为断言 |
| PIPE-44 | 上传中断 | 重跑续传（相同 ID 覆盖） |
| PIPE-45 | Pinecone 连接失败 | 3 次 retry 后报错，进程退出非 0 |
| PIPE-46 | batch upsert 失败 1 次 | retry 该批 |

### 4.6 `04_verify_pinecone.py` 检索验证

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-50 | 6 个测试 query（中英各 3） | 6/6 命中 |
| PIPE-51 | top-3 结果 score 全部 > 0.3 | PASS |
| PIPE-52 | Query 加 "query: " 前缀 | 实际行为断言 |
| PIPE-53 | 0 个向量时 | 友好提示运行 03 |

### 4.7 `extract_vocab.py` 词表提取

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-60 | 114 个词正常提取 | 22+92 |
| PIPE-61 | 词格式：word /phonetic/ pos. translation | 正则匹配 |
| PIPE-62 | 同 unit 重复词去重 | 唯一性断言 |
| PIPE-63 | 空 Vocabulary 页 | 跳过 |
| PIPE-64 | 非标准格式（无音标） | 跳过或部分提取 |

### 4.8 端到端流水线测试

| 编号 | 场景 | 期望 |
|------|------|------|
| PIPE-E2E-01 | 删 data/ → 重跑 00a→00b→00c→02→03→04 | 6 步全部 PASS，Pinecone 状态可恢复 |
| PIPE-E2E-02 | 增量更新（换 sem2 PDF） | 只重跑受影响步骤 |
| PIPE-E2E-03 | 流程中途 kill 进程 | 重跑幂等，不残留半成品 |

---

## 5. 性能测试

> 原则：所有性能数字要在**自己机器上**做基线测试，不依赖云端。target 是 M1 MacBook 16GB 单机。

### 5.1 测试方法

- **后端吞吐**：locust（用户脚本可加压）+ 监控 uvicorn 内存
- **延迟**：用 `time` 包裹 API 调用，统计 P50/P95/P99
- **嵌入模型**：单独测试 `model.encode(["passage: test"])` 时间
- **OCR**：跑 146 页，统计总时间

### 5.2 后端 API 延迟基线（M1 MPS 加速，MiniMax M3）

| 端点 | P50 | P95 | 阈值（fail） |
|------|------|------|------|
| POST /api/health | < 50ms | < 100ms | > 500ms |
| POST /api/auth/login | < 200ms | < 500ms | > 2s |
| POST /api/auth/register | < 300ms | < 800ms | > 2s |
| GET /api/me | < 100ms | < 300ms | > 1s |
| POST /api/chat/sync (单条) | 3-5s | 8s | > 15s |
| POST /api/chat/stream (首字) | 0.8-1.5s | 3s | > 5s |
| POST /api/chat/stream (全文) | 4-7s | 12s | > 20s |
| POST /api/quiz/generate (3题) | 10-15s | 25s | > 40s |
| POST /api/quiz/grade | 2-3s | 5s | > 10s |
| GET /api/progress/summary | < 100ms | < 300ms | > 1s |
| GET /api/progress/records | < 100ms | < 300ms | > 1s |
| GET /api/history/sessions | < 200ms | < 500ms | > 1s |
| GET /api/history/sessions/{id} | < 300ms | < 800ms | > 2s |
| GET /api/vocab/practice?n=10 | < 100ms | < 300ms | > 1s |

### 5.3 并发测试（locust）

| 场景 | 用户数 | 持续 | 阈值 |
|------|--------|------|------|
| 聊天压测 | 5 用户，每用户 1 QPS | 5 分钟 | 失败率 < 1%，P95 < 15s |
| Quiz 压测 | 2 用户，每用户 1 题/分钟 | 5 分钟 | 失败率 < 5%（考虑 M3 截断） |
| 词汇练习 | 10 用户，每用户 1 次/秒 | 2 分钟 | 失败率 < 0.5% |

**资源占用预期**（M1 16GB）：
- 后端进程 idle: 800MB（sentence-transformers 模型加载）
- 5 用户并发聊天：≤ 1.5GB
- Pinecone 网络出口：≤ 1MB/s

### 5.4 嵌入模型加载时间

```
冷启动（首次）：15-30s（下载 + 加载）
热启动（已缓存）：2-3s（仅加载到内存）
```

**测试**：在 main.py `lifespan` 中加 `print(f"loaded in {elapsed:.1f}s")`。

### 5.5 OCR 性能（M1 MPS 加速）

| 文档 | 总时间 | 速度 | 备注 |
|------|--------|------|------|
| 上册 146 页 (原生) | 0（不 OCR） | — | 直接 extract text |
| 下册 146 页 (M3 OCR) | 10-20 分钟 | ~10s/页 | 含网络延迟 |
| 下册 146 页 (EasyOCR) | 20-35 分钟 | ~15-20s/页 | 完全本地 |

### 5.6 Pinecone 查询延迟

```
平均: 80-150ms
P95: < 300ms
P99: < 500ms
```

### 5.7 内存泄漏检测

- 用 `memray` 或 `tracemalloc` 跑 100 次聊天循环
- 断言：单次聊天后内存增长 < 5MB
- 跑 1000 次后总增长 < 100MB

### 5.8 前端首屏性能（生产 build）

| 指标 | 目标 |
|------|------|
| 首次内容渲染 (FCP) | < 1.5s |
| 最大内容渲染 (LCP) | < 2.5s |
| 累积布局偏移 (CLS) | < 0.1 |
| 聊天首字响应 (TTFB) | < 1s |

工具：Lighthouse CI 集成到 GitHub Actions。

### 5.9 性能基线记录位置

`docs/PERFORMANCE_BASELINE.md`（待建），每次发布前更新数字。

---

## 6. AI 模型效果评估

> 这一节是项目**最特殊**的测试——AI 输出是非确定的，无法用单元测试验证。必须建立**评测集**+**自动+人工**混合评估。

### 6.1 评估维度总览

| 维度 | 谁评估 | 频率 | 工具 |
|------|--------|------|------|
| RAG 检索质量 | 自动 | 每次索引变更 | 自建 eval 脚本 |
| 对话回答质量 | 人工为主 | 每周抽 50 条 | LLM-as-judge 辅助 |
| 出题质量 | 人工+LLM | 每次 prompt 调整 | 题目难度分布 + 正确率 |
| 批改准确率 | 人工 | 每月抽 100 条 | 对照标准答案 |
| OCR 准确率 | 自动 | 每次换 OCR 引擎 | CER（字符错误率） |

### 6.2 RAG 检索质量

#### 6.2.1 评测集构造

`data/eval/rag_eval.jsonl`：
```json
{"query":"什么是过去进行时？","relevant_units":["Unit 5"],"relevant_sections":["Grammar Focus"]}
{"query":"ice skating 的恐惧","relevant_units":["Unit 1"],"relevant_sections":["Section A"]}
{"query":"Unit 3 的 Section B","relevant_units":["Unit 3"],"relevant_sections":["Section B"]}
```

**目标规模**：50-100 条，覆盖：
- 中文 query（30%）
- 英文 query（50%）
- 模糊 query（20%，如"那个语法"）

#### 6.2.2 指标

| 指标 | 目标 | 含义 |
|------|------|------|
| **Recall@5** | ≥ 0.85 | Top-5 中有 ≥ 1 个相关 chunk |
| **Recall@10** | ≥ 0.92 | Top-10 中有 ≥ 1 个相关 chunk |
| **MRR (Mean Reciprocal Rank)** | ≥ 0.70 | 第一个相关 chunk 的平均位置 |
| **NDCG@5** | ≥ 0.75 | 考虑排序质量 |
| **平均 score** | ≥ 0.50 | 实际检索的相关性分 |

#### 6.2.3 评测脚本骨架

```python
# scripts/eval_rag.py
def evaluate(jsonl_path: str = "data/eval/rag_eval.jsonl"):
    model = SentenceTransformer("intfloat/multilingual-e5-large")
    index = connect_pinecone()
    total = {"recall@5": 0, "mrr": 0, "ndcg@5": 0}
    for line in open(jsonl_path):
        item = json.loads(line)
        query_vec = model.encode(f"query: {item['query']}").tolist()
        results = index.query(vector=query_vec, top_k=10, include_metadata=True)
        # 计算各项指标
        # ...
    return total
```

### 6.3 对话回答质量

#### 6.3.1 评测集构造

`data/eval/chat_eval.jsonl`：
```json
{
  "query": "什么是过去完成时？",
  "expected_points": ["时态结构", "使用场景", "例句"],
  "expected_sources": [{"unit":"Unit 8","section":"Grammar Focus"}],
  "difficulty": "medium"
}
```

**目标规模**：30-50 条。每月增 5 条。

#### 6.3.2 评估方法

**LLM-as-judge**（用更强的模型评分）：

```
Prompt:
你是严格的英语教材评估员。学生提问：{query}
AI 回答：{response}

请按 5 分制评分（1=很差，5=很好）：
1. 准确性：内容是否正确？(25%)
2. 完整性：是否覆盖 expected_points？(25%)
3. 来源准确性：sources 是否与回答一致？(25%)
4. 可读性：是否适合八年级学生？(25%)

输出 JSON：{"score":4.2, "comment":"..."}
```

**人工抽检**：每周 50 条对话，2 名评估员独立打分，Krippendorff α ≥ 0.7。

#### 6.3.3 合格标准

- LLM-judge 平均分 ≥ 4.0
- 人工评估员平均分 ≥ 3.8
- 任何一项维度平均分 < 3.0：触发 prompt 优化

### 6.4 出题质量

#### 6.4.1 评测集构造

**人工标注集**（不依赖 M3）：
- 准备 10 个 Unit × 5 道题 = 50 道标准题（教师出）
- 含答案、解析、难度标注

#### 6.4.2 指标

| 指标 | 目标 | 含义 |
|------|------|------|
| 题目合理性（人工） | ≥ 4.0/5 | 题意清晰、选项干扰合理 |
| 答案准确性 | 100% | 答案必须正确（绝对指标） |
| 难度分布 | 0.3/0.5/0.2 (易/中/难) | 不能全简单或全难 |
| **解析质量** | ≥ 4.0/5 | 中文解析对八年级有用 |
| **题型多样性** | 1 单选 / 0.5 填空 / 0.5 翻译 | 防止全单选 |

#### 6.4.3 测试方法

- 用生成题目 vs 标注集对比答案（仅查答案准确性）
- 用 LLM-as-judge 评估合理性 + 解析质量
- 人工抽查 10%

### 6.5 批改准确率

#### 6.5.1 评测集构造

| 类型 | 题数 | 答案 |
|------|------|------|
| 单选 | 30 | 4 个选项 + 1 答案 |
| 填空 | 20 | 1 标准答案 + 5 个变体（同义/拼写错） |
| 翻译 | 20 | 1 标准答案 + 5 个变体 |

**3 种分数段**：完全对 1.0 / 部分对 0.6-0.8 / 完全错 0.0

#### 6.5.2 指标

| 指标 | 目标 |
|------|------|
| 单选批改准确率 | ≥ 99% |
| 填空批改准确率 | ≥ 90% |
| 翻译批改准确率 | ≥ 80% |
| 综合 score 与人工打分相关系数 | ≥ 0.85 |

#### 6.5.3 测试方法

- 100 道题 + 学生答案 → 喂给 grade_answer
- 对比 AI 输出与人工标准答案的 score 偏差
- 计算 score 与人工 score 的 Pearson 相关系数

### 6.6 OCR 准确率

#### 6.6.1 评测方法

- 选 10 页教材（10 张图片）作为"标准集"
- 人工抄录 10 页的纯文本作为 ground truth
- OCR 输出 vs ground truth → CER（字符错误率）

#### 6.6.2 指标

| 引擎 | CER 目标 | 备注 |
|------|---------|------|
| M3 Vision (当前) | < 5% | 含中文 |
| EasyOCR (备选) | < 10% | 备选，精度差 |
| PaddleOCR | 不测 | 已禁用 |

#### 6.6.3 测试脚本

`scripts/eval_ocr.py`：CER = (substitutions + deletions + insertions) / ground_truth_length

### 6.7 评估结果记录位置

`data/eval/results/{date}_*.json` 每次评估的快照。`docs/AI_EVAL_HISTORY.md` 趋势。

---

## 7. AI 模型微调计划

> **核心问题：要不要微调？什么时候微调？**

### 7.1 当前项目使用模型

| 角色 | 模型 | 是否微调 | 原因 |
|------|------|---------|------|
| 嵌入 | `intfloat/multilingual-e5-large` | ❌ | 开源、效果已很好 |
| OCR | MiniMax M3 Vision | ❌ | 通用模型，无需微调 |
| 对话 | MiniMax M3 | ❌ | 通过 prompt 工程优化 |
| 出题/批改 | MiniMax M3 | ❌ | 同上 |

### 7.2 决策原则：什么情况下才考虑微调

按"先易后难"原则：

| 优先级 | 优化手段 | 何时做 | 成本 | 收益 |
|--------|---------|--------|------|------|
| 1 | **Prompt 工程** | 任何问题先试 | 低 | 中 |
| 2 | **Few-shot examples** | Prompt 不够 | 低 | 中 |
| 3 | **RAG 优化**（query rewrite、rerank） | 检索质量差 | 中 | 高 |
| 4 | **改用更强模型** | Prompt/微调都不行 | 中 | 高 |
| 5 | **微调** | 上述都不行 + 有大量标注数据 | 极高 | 取决于场景 |

**经验法则**（来自 OpenAI/Anthropic 实践）：
- 90% 的"AI 质量"问题用 prompt + RAG 解决
- 微调只在你有**特定风格/格式/领域知识**硬要求时才有意义
- 微调**不会让模型变聪明**（基础能力来自预训练），只会让输出更符合特定风格

### 7.3 当前项目已踩的 AI 问题（v3.2 现状）

| 问题 | 是否需要微调 | 原因 |
|------|------------|------|
| M3 输出 `<think>` 块 | ❌ | prompt 禁用 + parser 剥离即可 |
| M3 中文里用 ASCII 双引号 | ❌ | prompt 禁止 + parser 替换即可 |
| 出题 JSON 截断 | ❌ | top_k=2 + 极简 prompt + retry |
| 出题答案错误 | ❌ | 用 RAG 提供 ground truth，无须微调 |
| 回答语言有时偏英 | ❌ | 强化 system prompt "默认中文" |
| OCR 中文错字 | 视情况 | 大量错字才考虑 fine-tune 专用模型 |

**结论：当前所有问题都能 prompt 解决，暂不需要微调。**

### 7.4 何时启动微调

满足以下**所有**条件才启动：
1. Prompt 优化 3 次后无明显改善
2. 有 1000+ 条高质量标注数据
3. 业务对响应延迟极敏感（不能用 prompt 加长来补）
4. 评估集有清晰可量化的目标指标

**特别是第 2 条**：fine-tune 的命门是数据。1000 条人工标注的成本远高于 3 次 prompt 调优。

### 7.5 如果真要微调：plan

#### 7.5.1 训练数据准备

`data/training/`：
```
instruction_format/
├── chat/
│   ├── jsonl          # {"messages":[...]} 格式，OpenAI 标准
│   └── stats.md
├── quiz/
│   ├── jsonl
│   └── stats.md
└── grading/
    ├── jsonl
    └── stats.md
```

每条样本：
- 至少 1000 条（chat/quiz/grading 各 1000）
- 8 训练 : 1 验证 : 1 测试 划分
- 严格去重（避免污染测试集）

#### 7.5.2 训练流程

```bash
# 1. 准备数据
python scripts/training/01_prepare_data.py --task chat
# 2. LoRA 微调（成本低、效果可）
python scripts/training/02_lora_train.py \
  --base MiniMax-M3 \
  --data data/training/chat/ \
  --epochs 3 \
  --lora_rank 16
# 3. 评估对比
python scripts/training/03_eval_compare.py \
  --base MiniMax-M3 \
  --finetuned ./checkpoints/chat-lora
```

#### 7.5.3 回归测试

微调后**必须**回跑：
- 全部功能测试（§2）— 确保不回归老功能
- 全部 AI 评估（§6）— 量化对比 base vs fine-tuned
- 出题成功率、批改准确率、回答质量

**门槛**：fine-tuned 必须在评估集上**所有指标** ≥ base，**且**不破坏现有功能。

### 7.6 微调 vs RAG：替代关系

很多场景下**强化 RAG 比微调更有效**：
- 微调让模型"记住"知识 → 知识更新要重新训练
- RAG 让模型"查阅"知识 → 改文档即更新
- 对于"教材内容问答"这类事实型任务，RAG **几乎总是**更优

**我们的策略**：先 RAG 做到极限，再考虑微调。

---

## 8. Harness / 自动化测试基础设施

### 8.1 整体架构

```
                    ┌──────────────┐
                    │   Git Push   │
                    └──────┬───────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   GitHub Actions CI    │
              └────────────┬───────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────┐      ┌──────────┐
   │  Lint   │      │ Unit/    │      │  E2E     │
   │  + Type │      │ Integ    │      │  (Play-  │
   │  Check  │      │  Tests   │      │  wright) │
   └─────────┘      └────┬─────┘      └──────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Coverage 报告 │
                  │ + Slack 通知  │
                  └───────────────┘
```

### 8.2 后端：pytest + httpx

#### 8.2.1 pyproject.toml 配置

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --cov=backend --cov-report=term-missing --cov-fail-under=70"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests that need real Pinecone/MiniMax",
]
```

#### 8.2.2 conftest.py 关键 fixture

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine
import tempfile, os

@pytest_asyncio.fixture
async def db():
    """每个测试独立临时 SQLite。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    # ...create tables...
    yield engine
    os.unlink(path)

@pytest_asyncio.fixture
async def async_client(db):
    from backend.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_minimax():
    with patch("backend.dependencies.get_chat_client") as mock:
        mock.return_value = MockMiniMax()  # 内置录制的 response
        yield mock

@pytest.fixture
def mock_pinecone():
    with patch("backend.dependencies.get_pinecone_index") as mock:
        mock.return_value = MockPinecone()
        yield mock
```

#### 8.2.3 helpers/mock_minimax.py

```python
class MockMiniMax:
    """录制/回放 MiniMax M3 response。"""
    def __init__(self, fixtures_dir: str = "tests/fixtures/minimax"):
        self.responses = self._load(fixtures_dir)

    def _load(self, path):
        # 加载 .json 文件，按 prompt hash 索引
        return {...}

    def chat_completions_create(self, **kwargs):
        prompt_hash = hash(frozenset(kwargs["messages"]))
        if prompt_hash in self.responses:
            return self.responses[prompt_hash]
        # 录制模式：实际调 M3 并保存
        return openai.actual_call(**kwargs)
```

**优势**：CI 不消耗 token、速度快 100x、可重现。

### 8.3 前端：Jest + React Testing Library + MSW

```json
// frontend/package.json scripts
{
  "test": "jest",
  "test:watch": "jest --watch",
  "test:coverage": "jest --coverage",
  "test:e2e": "playwright test"
}
```

**jest.config.js**：
```js
module.exports = {
  testEnvironment: "jsdom",
  setupFilesAfterEach: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/$1" },
  collectCoverageFrom: ["**/*.{ts,tsx}", "!**/*.d.ts", "!app/layout.tsx"],
  coverageThreshold: { global: { lines: 70, branches: 60 } },
};
```

**MSW (Mock Service Worker)** 拦截 fetch：
```ts
// tests/handlers.ts
import { http, HttpResponse } from "msw";
export const handlers = [
  http.post("/api/chat/sync", () =>
    HttpResponse.json({ content: "test response", sources: [] })
  ),
];
```

### 8.4 E2E：Playwright

```python
# frontend/e2e/auth.spec.py
from playwright.sync_api import expect, sync_playwright

def test_register_login_chat():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:3000/login")

        # 注册
        page.get_by_role("tab", name="注册").click()
        page.get_by_label("用户名").fill("e2e_user")
        page.get_by_label("密码").fill("e2e_pass")
        page.get_by_role("button", name="注册").click()

        # 应该在 /
        expect(page).to_have_url("http://localhost:3000/")
        expect(page.get_by_text("EnglishMaster")).to_be_visible()

        # 发消息
        page.get_by_role("textbox").fill("什么是过去进行时？")
        page.get_by_role("button", name="发送").click()

        # 等待 AI 回复
        page.wait_for_selector("text=过去进行时", timeout=15_000)
        browser.close()
```

**E2E 范围（不追求全覆盖）**：
- 核心 user journey：注册 → 聊天 → 出题 → 批改 → 看进度
- 5 个 journey 足够，不要更多

### 8.5 GitHub Actions CI

#### 8.5.1 `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e .
      - run: pytest tests/ --cov=backend --cov-fail-under=70
        env:
          PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}
          MINIMAX_API_KEY: ${{ secrets.MINIMAX_API_KEY }}

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run test -- --coverage
      - run: cd frontend && npm run build

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d
      - uses: actions/setup-python@v5
      - run: pip install playwright pytest-playwright
      - run: playwright install chromium
      - run: pytest frontend/e2e/ --browser chromium
```

#### 8.5.2 报告与通知

- **Codecov** 自动收集覆盖率
- **GitHub Status Check**：PR 必须通过
- **Slack 通知**（可选）：失败时 @oncall

### 8.6 测试覆盖率目标

| 层级 | 目标 | 说明 |
|------|------|------|
| 单元测试 | ≥ 70% | 行覆盖 |
| 集成测试 | ≥ 80%（核心 API） | 端到端 API 协议 |
| E2E | 5 个核心 user journey | 跑通关键路径 |
| AI 评估 | 30-100 条 | 量化 + 趋势 |

### 8.7 性能基线监控

GitHub Actions 加一个 `benchmark.yml` 每周跑一次：
- 后端：locust 5 分钟压测 → 对比 `docs/PERFORMANCE_BASELINE.md`
- 差异 > 20% 报警

### 8.8 本地开发者体验

```bash
# 改代码前
make test-fast        # 只跑 unit（< 30s）

# 提 PR 前
make test-all         # unit + integration（< 5min）
make test-e2e         # E2E（< 5min）

# 每周一次
make bench            # 性能压测（< 10min）
```

`Makefile` 包装命令，让开发者不必记脚本路径。

---

## 9. 质量门禁与发布标准

### 9.1 Phase 完成的硬性标准

每个 Phase 必须满足**所有**才算完成：

| Phase | 交付 | 质量门禁 |
|-------|------|---------|
| Phase 0 数据 | Pinecone 841+ vectors | `04_verify_pinecone` 6/6 通过，recall@5 ≥ 0.85 |
| Phase 1 后端核心 | /api/chat/sync + /stream | 流式首字 < 1.5s，sync P95 < 8s |
| Phase 2 出题 | /api/quiz/* | 出题成功率 ≥ 80%（5/5），批改 0 个 500 |
| Phase 3 前端 | / 聊天页 | E2E 通过：登录→发消息→看到回复 |
| Phase 4 测验前端 | /quiz | E2E 通过：出题→作答→批改→完成 |
| Phase 5 进度 | /api/progress/* + /api/vocab/* | 进度统计数字与 DB 一致 |
| Phase 6 多用户 | /api/auth/* | 跨用户隔离测试 100% 通过 |
| Phase 7+ 模式标签 | UI 显示 mode | 历史回放 6/6 模式正确 |

### 9.2 发布前必过项

- [ ] 所有 P0 bug 已修
- [ ] 单测覆盖率 ≥ 70%
- [ ] 集成测试全部通过
- [ ] 5 个核心 E2E journey 通过
- [ ] AI 评估集上 recall@5 ≥ 0.85、批改准确率 ≥ 90%
- [ ] 性能基线无 > 20% 退化
- [ ] 无 P1 安全漏洞（依赖扫描：`pip-audit`、`npm audit`）
- [ ] AGENTS.md 坑位表已更新到当前已知问题
- [ ] 文档（README + 开发文档 + AGENTS.md）已同步

### 9.3 Bug 严重度定义

| 级别 | 含义 | 例子 | SLA |
|------|------|------|------|
| **P0** | 阻塞核心功能 | 登录失败、聊天返回 500、OCR 完全失败 | 24h 内修 |
| **P1** | 影响体验但有 workaround | 部分页加载慢、出题偶发失败、UI 错位 | 1 周内修 |
| **P2** | 小瑕疵 | 文案错别字、loading 转圈不消失 | 2 周内修 |
| **P3** | 改进项 | 重构、文档、命名 | 不限期 |

### 9.4 不接受的妥协

- ❌ 跳过 P0 验证（00c/04 必须跑）
- ❌ Pinecone 维度不匹配就上传
- ❌ 禁用 PaddleOCR 后又引入
- ❌ 任何接口在生产没有 retry 装饰
- ❌ E5 模型不加 passage: / query: 前缀

---

## 10. 风险评估与缓解

### 10.1 已知风险矩阵

| # | 风险 | 影响 | 概率 | 缓解 | 监控信号 |
|---|------|------|------|------|---------|
| R-01 | **OCR 准确率不足** | 词条错、Pinecone 检索质量低 | 中 | 00c 验证、CR ≥ 60% | CER 指标 |
| R-02 | **M3 API 变更/下线** | 全部对话/出题失败 | 低 | 抽象 `chat_client` 接口，可换 Claude/其他 | API 错误率 |
| R-03 | **Token 成本失控** | 每月账单超预算 | 中 | max_tokens 限值、retry 防失控、单元测试 mock | 月度 token 报表 |
| R-04 | **OCR Unit 125 误识别** | 词表归类错 | 高 | 已知问题，记录文档 | `00c_verify_ocr` 输出 |
| R-05 | **E5 模型被 HuggingFace 下架** | 嵌入失败 | 极低 | 本地已缓存，缓存策略 + 备用模型 | 启动检查 |
| R-06 | **Pinecone Index 被删** | 全部向量丢失 | 极低 | 备份 raw_pages JSON，可重跑 03 | describe_index_stats |
| R-07 | **SQLite 数据损坏** | 进度数据丢失 | 低 | 每周自动备份（待实现） | DB 完整性检查 |
| R-08 | **JWT secret 泄露** | 任意用户被冒充 | 中 | 强制 32+ 字符 secret、定期 rotate | secret 强度检查 |
| R-09 | **慢查询 / Pinecone 限流** | API 慢或失败 | 中 | Pinecone 免费版限额、监控 429 | API 延迟告警 |
| R-10 | **OCR 输出超 max_tokens 截断** | 出题返回 500 | 中（已发生） | 4 步组合修复（§23.6） | 5/5 成功率 |
| R-11 | **M3 智能引号破坏 JSON** | grade 500 | 中（已发生） | 3 层防护（§23.7） | grade 错误率 |
| R-12 | **MiniMax M3 配额耗尽** | 全部 AI 功能停摆 | 低 | Token Plan 月度计费、监控用量 | 余额监控 |
| R-13 | **OCR mini-batch 内存峰值** | M1 16GB 可能 OOM | 低 | top_k=2 已减、批 100 验证 | memray 监控 |
| R-14 | **前端构建缓存导致 stale UI** | 用户看到旧版本 | 中 | 浏览器自动 refresh、CSP no-cache | E2E 跑最新 build |
| R-15 | **测试数据污染生产** | 用户数据被覆盖 | 中 | 严格 .gitignore、CI 用 secrets | 审计 `.env` |

### 10.2 应对预案

#### R-02 M3 API 变更
```python
# 切换只需改 .env
CHAT_PROVIDER=minimax  # 当前
# 未来
CHAT_PROVIDER=anthropic
CHAT_PROVIDER=aliyun
```
- `dependencies.py` 用 `get_chat_client()` 工厂
- 切换时跑完 §6 评估集

#### R-03 Token 成本失控
- max_tokens 上限：出题 3000→6000 retry、对话 2048、批改 600
- 月预算告警：设置 billing alarm
- 大请求优先用 mock（开发期）

#### R-10 截断
- 已实施：top_k=2 + 极简 prompt + retry + parse_json 渐进式
- 监控：每次出题成功率，< 80% 触发 prompt 优化

### 10.3 应急流程

| 场景 | 第一时间 | 后续 |
|------|---------|------|
| M3 API 全挂 | 切到 mock 模式（"AI 暂时不可用"） | 联系 MiniMax 工单 |
| Pinecone 不可用 | 后端返回降级（无 RAG 上下文） | 排查网络/认证 |
| OCR 失败 | 改用 EasyOCR fallback | 修复 M3 配额 |
| 测试覆盖率掉 | 禁止 merge | 补测试 |

### 10.4 待办（按优先级）

| 优先级 | 待办 | 估计工时 |
|--------|------|---------|
| P1 | pytest + httpx 单测框架 | 1 天 |
| P1 | GitHub Actions CI | 0.5 天 |
| P2 | Playwright E2E | 1 天 |
| P2 | AI 评估集构造（30+ 条） | 0.5 天 |
| P3 | RAG 评估脚本 | 0.5 天 |
| P3 | OCR 评估脚本 | 0.5 天 |
| P3 | 性能基线工具 | 1 天 |
| P3 | SQLAlchemy Alembic 迁移 | 1 天（生产前必做） |
| P3 | 监控面板（Grafana） | 1 天 |

---

## 附录 A：执行清单（Checklist）

- [ ] §8.1 创建 pyproject.toml / pytest 配置
- [ ] §8.1 创建 conftest.py + helpers/
- [ ] §8.2 创建 M3 mock + 录制 50 个 response fixture
- [ ] §2 写完所有 pytest 用例（200+ 用例）
- [ ] §3 写完所有 Jest 用例（100+ 用例）
- [ ] §3.4 创建 E2E 5 个 journey
- [ ] §6.2 构造 RAG 评估集 50-100 条
- [ ] §6.3 构造对话评估集 30-50 条
- [ ] §6.4 构造出题标注集 50 道
- [ ] §6.5 构造批改测试集 100 道
- [ ] §6.6 构造 OCR ground truth 10 页
- [ ] §8.5 写 GitHub Actions
- [ ] §9.2 发布前清单跑通一遍

---

*文档版本：v1.0 | 状态：待评审*
*配套文档：README.md、AGENTS.md、docs/初中英语AI学习Agent开发文档.md*
