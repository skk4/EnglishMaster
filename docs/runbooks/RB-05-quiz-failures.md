# RB-05：出题/批改 5xx 激增

> **场景**：`/api/quiz/*` 5xx 错误率 > 5%
> **严重度**：P1
> **首响 SLA**：1 h

## 症状

- `/api/quiz/generate` 大量 500
- Sentry 报错 `parse_json_response failed` 或 `max_tokens`
- 用户反馈"出题失败"

## 排查

```bash
# 1. 看后端日志
railway logs --tail 500 | grep -E "quiz|parse_json" | tail -20

# 2. 找失败的 prompt 内容
railway logs | grep -A 30 "parse_json_response failed" | head -50
```

### 根因分类
- **A. M3 截断**：`len=969` 等异常短 → 减小 max_tokens 不会解决，反而需要加大
- **B. M3 双引号破坏 JSON**：correction 字段里 `"我想..."` → prompt 修复
- **C. M3 整体返回损坏**：timeout / network → 切 provider

## 缓解

### 立即动作（5min）
- 前端"重试"按钮已就绪
- 在 Slack 通知用户"AI 繁忙，请稍后重试"

### 短期优化（30min）
```python
# backend/services/quiz_service.py

# 1. 减小 RAG 上下文（已做：top_k=2）
# 2. 极简 prompt（已做）
# 3. retry 加大 max_tokens（已做：6000）
# 4. 新增：彻底失败时 fallback
try:
    result = self._call_quiz_api(prompt, max_tokens=3000, strict=False)
except ValueError:
    try:
        result = self._call_quiz_api(prompt, max_tokens=6000, strict=True)
    except ValueError:
        # 两次都失败：返回上一缓存的题目 / 备用题
        result = self._get_cached_questions(unit)  # 临时方案
```

### 长期方案
- 用更稳定的 prompt 模板（few-shot）
- 多 provider 备份（M3 失败 → Claude / OpenAI）

## 验证

```bash
# 跑 10 次出题
for i in {1..10}; do
  curl -X POST /api/quiz/generate \
    -H "Content-Type: application/json" \
    -d '{"unit":"Unit 1","semester":1,"quiz_type":"multiple_choice","count":3}'
  sleep 5
done
# 期望：≥ 8/10 成功

# 看 Sentry 错误率下降
# 看 Grafana 错误率 < 1%
```

## 关联

- 文档：TEST_PLAN §2.6 (QUIZ-* 用例)
- 监控：A-09（出题成功率低）
- 已修坑位：#23、#24
