# 评估集说明

> 这是项目"AI 质量"评估的种子集，详细见 [TEST_PLAN §6](../docs/TEST_PLAN.md#6-ai-模型效果评估)。
> **当前规模**：仅供"冒烟测试"，生产前需扩展到 50-100 条/类型。

## 文件结构

```
data/eval/
├── README.md                   # 本文件
├── rag_eval.jsonl              # RAG 检索质量评测集
├── chat_eval.jsonl             # 对话回答质量评测集
├── quiz_groundtruth.jsonl      # 出题标准答案集（教师出题）
└── grading_eval.jsonl          # 批改测试集（带分数预期）
```

## 评测方法

### RAG 检索评测

```python
# scripts/eval_rag.py (待建)
import json
for line in open("data/eval/rag_eval.jsonl"):
    item = json.loads(line)
    query_vec = model.encode(f"query: {item['query']}")
    results = index.query(vector=query_vec, top_k=10, include_metadata=True)
    # 计算 recall@5, MRR, NDCG
    # ...
```

**指标目标**（TEST_PLAN §6.2.2）：
- Recall@5 ≥ 0.85
- MRR ≥ 0.70
- NDCG@5 ≥ 0.75

### 对话质量评测

用 LLM-as-judge（详见 TEST_PLAN §6.3.2）：

```python
judge_prompt = f"""
你是严格的英语教材评估员。
学生提问：{query}
AI 回答：{response}
参考要点：{expected_points}
请按 5 分制评分：准确性 25% / 完整性 25% / 来源准确性 25% / 可读性 25%
"""
```

### 出题质量评测

对比 AI 出题与 `quiz_groundtruth.jsonl` 的答案（仅查答案准确性），其他维度用 LLM-as-judge。

### 批改质量评测

用 `grading_eval.jsonl` 喂给 `grade_answer`，对比 AI 输出与 `score_expected` 字段：
- score 与 expected 偏差 < 0.1 → 视为正确
- 计算"批改准确率"= 正确数 / 总数

## 扩展计划

| 集 | 当前 | 目标 | 截止 |
|------|------|------|------|
| rag_eval | 10 | 50 | Q3 2026 |
| chat_eval | 5 | 30 | Q3 2026 |
| quiz_groundtruth | 5 | 50 | Q4 2026 |
| grading_eval | 5 | 100 | Q4 2026 |

## 添加新样本的规范

每条样本最少包含：
- 唯一 ID
- 查询内容（query）
- 语言（zh / en）
- 期望来源（如适用）
- 难度（easy / medium / hard）

提交前用 `python scripts/eval_validate.py data/eval/rag_eval.jsonl` 验证格式。
