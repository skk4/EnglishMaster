# RB-02：Pinecone 不可用

> **场景**：RAG 检索失败，AI 回答"找不到相关内容"
> **严重度**：P1（功能降级但部分可用）
> **首响 SLA**：1 h

## 症状

- `/api/chat/sync` 返回 200 但 `sources=[]`
- `/api/chat/stream` 流式结束但无来源引用
- 后端日志含 `PineconeApiException` / `IndexNotFound` / `Connection timeout`

## 排查

### 1. 确认 Pinecone 端
```bash
curl -H "Api-Key: $PINECONE_API_KEY" \
  https://xsjkndb01-f408jww.svc.aped-4627-b74a.pinecone.io/describe_index_stats

# 期望：{"dimension":1024,"total_vector_count":841,...}
```

### 2. 检查后端连接
```bash
railway logs --tail 100 | grep -i "pinecone"
# 看是否有认证错误、超时
```

### 3. 检查环境变量
```bash
railway variables | grep PINECONE
# 确认 API key 正确，Host URL 正确
```

## 缓解

### 短期（5min）
**RAG 降级模式**：让 AI 不用 RAG 上下文也能回答（基于通用知识）。

```python
# backend/services/rag_service.py
def retrieve(self, query, ...):
    try:
        return self._retrieve_from_pinecone(query, ...)
    except Exception as e:
        logger.error(f"RAG failed, fallback to no-context: {e}")
        return []  # 空列表 → context = "No relevant content"
```

### 中期（30min）
- 联系 Pinecone 支持
- 检查 Index 状态：`pc.describe_index("xsjkndb01")`

### 长期
- 缓存最近 1000 个 query 的 RAG 结果
- 多区域 Pinecone 副本

## 验证恢复

```bash
# 1. Pinecone 健康
curl -H "Api-Key: $PINECONE_API_KEY" \
  $PINECONE_HOST/describe_index_stats

# 2. 实际问答含来源
curl -X POST /api/chat/sync -d '{"message":"过去进行时","mode":"grammar"}'
# 期望：content 末尾有 "教材来源" 列表

# 3. 04_verify_pinecone.py
python scripts/04_verify_pinecone.py
# 期望：6/6 通过
```

## 复盘

[Postmortem 模板](../postmortem/)

## 关联

- 监控：A-10
- 重建脚本：`python scripts/03_embed_and_upload.py`（约 5min）
