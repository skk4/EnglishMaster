# 贡献指南

> 欢迎贡献代码、文档、bug 报告、功能建议！

## 行为准则

请阅读 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)（采用 Contributor Covenant）。
所有贡献者都应遵守这些准则。

## 我能贡献什么？

| 类型 | 怎么贡献 |
|------|---------|
| 🐛 Bug 报告 | 提 [Issue](https://github.com/xsj/junior-english-agent/issues/new?template=bug_report.md) |
| ✨ 功能建议 | 提 [Issue](https://github.com/xsj/junior-english-agent/issues/new?template=feature_request.md) |
| 📖 文档改进 | 直接提 PR（小改动不需要先开 Issue） |
| 💻 代码 | 提 PR（请先开 Issue 讨论大改动） |
| 🌐 翻译 | 当前仅中文；翻译需求大时启动 |
| 🧪 测试 | 加测试用例或修失败的测试 |

## 提 PR 流程

### 1. 准备工作

```bash
# 克隆仓库
git clone https://github.com/xsj/junior-english-agent.git
cd junior-english-agent

# 创建分支（命名规范：type/scope）
git checkout -b feat/add-cloze-quiz          # 新功能
git checkout -b fix/quiz-truncation           # 修 bug
git checkout -b docs/update-test-plan        # 文档
git checkout -b refactor/extract-rag-service # 重构
```

### 2. 开发

```bash
# 装依赖
make install

# 改代码
# ...

# 跑测试（必须全过）
make test-fast

# 跑 lint（必须无错）
make lint
make format  # 自动修格式

# 端到端验证（涉及 UI 时）
make backend   # 终端 1
make frontend  # 终端 2
```

### 3. 提交

```bash
# 提交信息规范（用 imperative mood）
git commit -m "feat(quiz): add cloze test type"
git commit -m "fix(chat): strip <think> blocks from streaming output"
git commit -m "docs(test): add test cases for user isolation"
```

**格式**：`<type>(<scope>): <subject>`

| type | 用途 |
|------|------|
| feat | 新功能 |
| fix | 修 bug |
| docs | 文档 |
| refactor | 重构（不修 bug 不加功能） |
| test | 加测试 |
| chore | 杂项（依赖、配置） |
| docs | 文档 |
| perf | 性能优化 |

**scope**（可选）：`chat` / `quiz` / `auth` / `rag` / `db` / `frontend` / `backend` / `docs` 等

### 4. 推送并开 PR

```bash
git push origin feat/add-cloze-quiz
```

在 GitHub 上：
1. 开 Pull Request
2. 填 PR 模板（自动）
3. 关联相关 Issue
4. 等 CI 全过（GitHub Actions 自动跑）
5. 等 1 个 review
6. 合并

## 必读规范

- **[AGENTS.md](./AGENTS.md)** — 开发规范（禁用 PaddleOCR、E5 前缀、限流等）
- **[docs/TEST_PLAN.md](./docs/TEST_PLAN.md)** — 测试计划
- **[docs/OPS_PLAN.md](./docs/OPS_PLAN.md)** — 运维计划
- **[docs/PM_PLAN.md](./docs/PM_PLAN.md)** — 产品计划

## Definition of Done

- [ ] 代码写完
- [ ] 单测 + 集成测试通过
- [ ] 覆盖率不下降
- [ ] Lint 无 error
- [ ] AGENTS.md 坑位表更新（如果踩坑）
- [ ] 文档同步（README / 开发文档 / CHANGELOG）
- [ ] 部署到 staging 验证
- [ ] 1 个 reviewer approve

## 不接受的事

- ❌ 跳过测试
- ❌ 硬编码 secrets
- ❌ 提交大文件（PDF、OCR 缓存、数据库）到 Git
- ❌ 跳过 lint 警告
- ❌ 改文件不更新文档

## 开发环境

- Python 3.11
- Node.js 20+
- macOS 13+ / Linux / WSL2

## 报告问题

- [Bug 报告](.github/ISSUE_TEMPLATE/bug_report.md)
- [功能建议](.github/ISSUE_TEMPLATE/feature_request.md)
- [数据/OCR 问题](.github/ISSUE_TEMPLATE/data_issue.md)
- [安全漏洞](./SECURITY.md)

## 许可

提交代码即表示你同意按 [MIT LICENSE](./LICENSE) 授权你的贡献。
