# RB-01：MiniMax M3 API 不可用

> **场景**：所有 AI 对话/出题/批改返回 5xx 或超时
> **严重度**：P0（核心功能全挂）
> **首响 SLA**：30 min
> **解决 SLA**：4 h

## 症状

- `/api/chat/*` 返回 5xx
- `/api/quiz/*` 返回 5xx
- 后端日志含 `M3 API timeout` / `ConnectionError` / `AuthenticationError`
- Sentry 报错 `M3 unreachable`

## 排查

### 1. 确认是 M3 自身还是我们端
```bash
# 直接 curl 测试
curl -X POST https://api.minimax.io/v1/chat/completions \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M3","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'

# 期望：200 OK
# 如果非 200 → M3 端问题
# 如果 200 → 检查我们后端
```

### 2. 看后端日志
```bash
# Railway
railway logs --tail 200 | grep -i "minimax\|openai\|chat_complet"

# 自建
journalctl -u englishmaster-backend --since "5 min ago" | grep -i minimax
```

### 3. 检查 API key
```bash
railway variables | grep MINIMAX
# 确认不为空，未被 rotate 掉
```

## 缓解

### 短期（5min 内）
```bash
# 在前端显示"AI 暂时不可用"，降级模式
# 修改后端 chatbot_service，try/except 包住，fallback 到 "AI 繁忙，请稍后重试"
```

### 中期（30min）
- 联系 MiniMax 工单（如果有 SLA 合同）
- 切到备用 provider（需 `dependencies.py` 抽象层支持）

### 长期
- 实现 AI provider pool：M3 主、Claude/OpenAI 备
- 本地更小模型（如 Qwen-1.5B）做兜底

## 验证恢复

```bash
# 1. 后端健康
curl /api/health

# 2. 实际对话
curl -X POST /api/chat/sync -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"test","mode":"general"}'

# 3. 监控 5 分钟
# 看 Grafana 错误率回到 < 0.5%
```

## 复盘必做

[Postmortem 模板](../postmortem/2026-MM-DD-minimax-down.md)

## 关联

- 监控：A-02（错误率 > 5%）
- 文档：OPS_PLAN §5.3
- Runbook：RB-02（Pinecone 不可用）
