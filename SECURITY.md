# Security Policy

> **适用版本**：v3.2 起
> **最后更新**：2026-06-02

## 支持的版本

| 版本 | 支持状态 |
|------|---------|
| v3.2+ | ✅ 积极维护 |
| < v3.2 | ❌ 已停止维护 |

## 报告漏洞

**请勿在 GitHub Issues 公开报告安全漏洞。**

通过以下方式私密报告：

- **邮件**：security@englishmaster.com（建议）
- **GitHub Security Advisories**：https://github.com/xsj/junior-english-agent/security/advisories/new

**报告内容**：
- 漏洞简明描述
- 复现步骤 / PoC
- 潜在影响
- 你的环境信息（可选）
- 联系信息

**响应承诺**：
- 24 小时内确认
- 7 天内评估严重度
- 30 天内修复 P0/P1 漏洞
- 公开致谢（如报告者同意）

## 安全设计（已实施）

| 措施 | 状态 | 详情 |
|------|------|------|
| JWT 鉴权 | ✅ | HS256，≥ 32 字节 secret |
| 密码 hash | ✅ | SHA256 + 16 字节 salt |
| 多用户隔离 | ✅ | user_id 强制从 token 解析 |
| CASCADE 删除 | ✅ | 删 user 级联删所有数据 |
| 限流 | ✅ | 登录 10/5min、AI 30/min |
| 安全响应头 | ✅ | HSTS/CSP/X-Frame/Referrer |
| Request ID | ✅ | 所有日志/响应带 X-Request-ID |
| 错误脱敏 | ✅ | Sentry 发送前过滤 token/password |
| 输入消毒 | ✅ | OpenAI 反 prompt 注入（系统层） |

## 安全使用指南

### 用户

- **不要**把你的 JWT token 分享给别人
- **不要**在公共电脑保持登录
- **强密码**：≥ 4 字符（已强制，但建议更长）
- **隐私**：`docs/FAQ.md` 写明我们怎么处理数据

### 部署者

- **改 JWT_SECRET**：生产前必改（≥ 32 字节随机）
- **改默认密码**：管理员账户
- **HTTPS**：用 Cloudflare 代理（自动 HTTPS）
- **环境变量**：用 1Password/Doppler 集中管理，**绝不入 Git**
- **定期更新依赖**：`pip install -U`，Dependabot 自动 PR
- **审计日志**：生产环境配 Sentry

### 贡献者

- **绝不在代码里写 secrets**（`os.getenv()` 读 .env）
- **绝不在 git 历史里写 secrets**（pre-commit hook 扫描）
- **新依赖必查 CVE**：`pip-audit`、`npm audit`

## 已修复的安全问题

| 编号 | 描述 | 修复版本 | 致谢 |
|------|------|---------|------|
| — | （暂无公开披露） | — | — |

## 致谢

感谢所有负责任地报告安全问题的研究者。
