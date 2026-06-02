# Changelog

> 所有值得注意的项目变更都会记录在这里。
> 格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
> 版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- HTML 原型（`docs/prototypes/`）— 5 个核心页面
- 用户 FAQ（`docs/FAQ.md`）— 20 个常见问题
- 5 个 Runbook（`docs/runbooks/`）— M3/Pinecone/SQLite/磁盘/出题故障
- 数据评估集种子（`data/eval/`）— RAG/对话/出题/批改
- GitHub 配置：Issue 模板、PR 模板、CODEOWNERS、CI workflow、Dependabot
- Postmortem 模板（`docs/postmortem/`）

### Changed
- 开发文档 v3.1 → v3.2
- AGENTS.md 坑位 #19-26（含流式 think 块过滤）
- README 加 4 角色协作章节
- AI 流式输出：3 道防线过滤 think 块（prompt 禁止 + 后端状态机 + 前端兜底）
- 抽出 `strip_think_blocks` 共用函数（chat_history_service）

### Fixed
- 修了 quiz JSON 截断的 4 步组合
- 修了 grade 中文双引号破坏 JSON
- 修了 React Hooks 早 return 顺序
- 修了前端 4 个 GET 漏带 Authorization 头
- 修了聊天历史 bug + 加模式标签

## [v3.2.0] - 2026-06-02

### Added
- 对话历史持久化（chat_sessions + chat_messages 表）
- 多用户系统（注册/登录 + JWT）
- 出题/批改（3 种题型 + 自动批改）
- 进度追踪 + 词汇闪卡
- 前端 Next.js 14 完整聊天 UI
- Pinecone 841 向量入库
- MiniMax M3 OCR 跑通 146 页下册

### Fixed
- AGENTS.md v1.4 坑位更新

---

## 模板

```markdown
## [vX.Y.Z] - YYYY-MM-DD

### Added
- 新功能

### Changed
- 既有功能变化

### Deprecated
- 即将移除

### Removed
- 已移除

### Fixed
- 修 bug

### Security
- 安全相关
```

## 发布流程

1. 升级版本号（`v3.2.0` → `v3.3.0`）
2. 更新本文档 "Unreleased" → 正式版本
3. git tag `v3.3.0`
4. 触发 GitHub Action 自动部署
5. 通知 Slack #englishmaster
