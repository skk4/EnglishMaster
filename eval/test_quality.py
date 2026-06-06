"""
eval/test_quality.py — LLM 回答质量 + 批改准确性测试

测试目标：
  1. Ragas 三项指标：faithfulness / answer_relevancy / context_recall
  2. 批改准确性：选择题精确匹配 + 翻译题同义识别
  3. system prompt 行为规则：超纲拒绝 / 语气友善 / 格式正确

运行：
    pip install ragas datasets --break-system-packages
    .venv/bin/python -m pytest eval/test_quality.py -v -s
"""
import pytest

pytestmark = pytest.mark.real

# ══════════════════════════════════════════════════════
# 测试数据
# 根据你的课本实际内容调整 ground_truth
# ══════════════════════════════════════════════════════

KNOWLEDGE_CASES = [
    {
        "question":     "used to 怎么用？",
        "ground_truth": "used to + 动词原形，表示过去经常做某事或过去的状态，现在已不再如此",
    },
    {
        "question":     "outgoing 是什么意思？",
        "ground_truth": "外向的，形容性格开朗爱与人交往",
    },
    {
        "question":     "比较级怎么构成？",
        "ground_truth": "单音节词末尾加 er，多音节词前加 more，不规则变化如 good-better",
    },
    {
        "question":     "现在进行时的结构是什么？",
        "ground_truth": "be 动词（am/is/are）加动词 ing 形式",
    },
    {
        "question":     "What does the word 'creative' mean?",
        "ground_truth": "有创造力的，创意丰富的",
    },
]

GRADING_CASES = [
    {
        "label":          "标准答案",
        "question":       "翻译：我过去常常骑车上学",
        "correct_answer": "I used to ride a bike to school.",
        "student_answer": "I used to ride a bike to school.",
        "expected":       True,
    },
    {
        "label":          "同义表达 cycle=ride a bike",
        "question":       "翻译：我过去常常骑车上学",
        "correct_answer": "I used to ride a bike to school.",
        "student_answer": "I used to cycle to school.",
        "expected":       True,
    },
    {
        "label":          "时态错误",
        "question":       "翻译：我过去常常骑车上学",
        "correct_answer": "I used to ride a bike to school.",
        "student_answer": "I am riding a bike to school.",
        "expected":       False,
    },
    {
        "label":          "缺少 used to 结构",
        "question":       "翻译：我过去常常骑车上学",
        "correct_answer": "I used to ride a bike to school.",
        "student_answer": "I ride bike to school before.",
        "expected":       False,
    },
]


# ══════════════════════════════════════════════════════
# Ragas 质量评测
# ══════════════════════════════════════════════════════

class TestRagasQuality:

    @pytest.fixture(autouse=True, scope="class")
    def check_ragas(self):
        try:
            import ragas
            import datasets
        except ImportError:
            pytest.skip(
                "ragas 未安装，请先运行：\n"
                ".venv/bin/pip install ragas datasets"
            )

    def _collect(self, client, auth):
        """批量调用接口，收集回答和 sources"""
        questions, answers, contexts, ground_truths = [], [], [], []
        for case in KNOWLEDGE_CASES:
            r = client.post("/api/chat/sync",
                headers=auth,
                json={"message": case["question"]}
            )
            assert r.status_code == 200
            data = r.json()
            questions.append(case["question"])
            answers.append(data["content"])
            ground_truths.append(case["ground_truth"])
            context_texts = [
                s.get("text", s.get("section", ""))
                for s in data["sources"]
            ]
            contexts.append(context_texts or ["未检索到课本内容"])
        return questions, answers, contexts, ground_truths

    def test_faithfulness(self, client, auth):
        """
        忠实度 > 0.7：回答有没有编造课本里没有的内容。
        分数低 → 加强 system prompt '必须基于该内容回答' 约束
        """
        from ragas import evaluate
        from ragas.metrics import faithfulness
        from datasets import Dataset

        q, a, c, g = self._collect(client, auth)
        result = evaluate(
            Dataset.from_dict({"question": q, "answer": a, "contexts": c, "ground_truth": g}),
            metrics=[faithfulness]
        )
        score = result["faithfulness"]
        print(f"\n  faithfulness: {score:.3f}")
        assert score > 0.7, (
            f"faithfulness={score:.3f}，幻觉率太高（目标 > 0.7）\n"
            "建议：加强 system prompt 第4条规则，限制只能基于检索内容回答"
        )

    def test_answer_relevancy(self, client, auth):
        """
        回答相关性 > 0.75：回答有没有切题。
        分数低 → 格式约束可能干扰了回答方向，检查 GRAMMAR_ADDITION
        """
        from ragas import evaluate
        from ragas.metrics import answer_relevancy
        from datasets import Dataset

        q, a, c, g = self._collect(client, auth)
        result = evaluate(
            Dataset.from_dict({"question": q, "answer": a, "contexts": c, "ground_truth": g}),
            metrics=[answer_relevancy]
        )
        score = result["answer_relevancy"]
        print(f"\n  answer_relevancy: {score:.3f}")
        assert score > 0.75, (
            f"answer_relevancy={score:.3f}，回答相关性太低（目标 > 0.75）"
        )

    def test_context_recall(self, client, auth):
        """
        召回率 > 0.6：Pinecone 有没有找到足够的课本内容。
        分数低 → top_k 从 2 调到 3 或 4，或重新检查切片方式
        """
        from ragas import evaluate
        from ragas.metrics import context_recall
        from datasets import Dataset

        q, a, c, g = self._collect(client, auth)
        result = evaluate(
            Dataset.from_dict({"question": q, "answer": a, "contexts": c, "ground_truth": g}),
            metrics=[context_recall]
        )
        score = result["context_recall"]
        print(f"\n  context_recall: {score:.3f}")
        assert score > 0.6, (
            f"context_recall={score:.3f}，RAG 召回率太低（目标 > 0.6）\n"
            "建议：把 quiz_service 的 top_k 从 2 调整到 3"
        )


# ══════════════════════════════════════════════════════
# 批改准确性测试
# ══════════════════════════════════════════════════════

class TestGradingAccuracy:

    def test_multiple_choice_correct(self, client, auth):
        """选择题答对 → is_correct=True, score=1.0"""
        r = client.post("/api/quiz/generate", json={
            "unit": "Unit 1", "semester": 1,
            "quiz_type": "multiple_choice", "count": 1
        })
        assert r.status_code == 200
        question    = r.json()["questions"][0]
        correct_ans = question["answer"]

        r2 = client.post("/api/quiz/grade",
            headers=auth,
            json={
                "question":      question,
                "student_answer": correct_ans,
                "unit": "Unit 1", "semester": 1
            }
        )
        assert r2.status_code == 200
        assert r2.json()["is_correct"] == True
        assert r2.json()["score"] == 1.0

    def test_multiple_choice_wrong(self, client, auth):
        """选择题答错 → is_correct=False"""
        r = client.post("/api/quiz/generate", json={
            "unit": "Unit 1", "semester": 1,
            "quiz_type": "multiple_choice", "count": 1
        })
        question    = r.json()["questions"][0]
        correct_ans = question["answer"]
        wrong_ans   = "B" if correct_ans != "B" else "A"

        r2 = client.post("/api/quiz/grade",
            headers=auth,
            json={
                "question":      question,
                "student_answer": wrong_ans,
                "unit": "Unit 1", "semester": 1
            }
        )
        assert r2.json()["is_correct"] == False

    @pytest.mark.parametrize("case", GRADING_CASES, ids=[c["label"] for c in GRADING_CASES])
    def test_translation_grading(self, client, auth, case):
        """
        翻译题批改准确性，含同义表达识别。
        最关键的场景：cycle 和 ride a bike 都正确。
        """
        r = client.post("/api/quiz/grade",
            headers=auth,
            json={
                "question": {
                    "type":     "translation",
                    "question": case["question"],
                    "answer":   case["correct_answer"],
                },
                "student_answer": case["student_answer"],
                "unit": "Unit 1", "semester": 1,
            }
        )
        assert r.status_code == 200, f"接口报错：{r.text}"
        is_correct = r.json()["is_correct"]
        assert is_correct == case["expected"], (
            f"\n批改结果不对！\n"
            f"  场景：{case['label']}\n"
            f"  学生答案：{case['student_answer']}\n"
            f"  期望：{'正确' if case['expected'] else '错误'}\n"
            f"  实际：{'正确' if is_correct else '错误'}\n"
            f"  反馈：{r.json().get('feedback', '')}"
        )

    def test_feedback_explains_error(self, client, auth):
        """批改错误答案时，feedback 必须解释原因"""
        r = client.post("/api/quiz/grade",
            headers=auth,
            json={
                "question": {
                    "type":     "translation",
                    "question": "翻译：我过去常常骑车上学",
                    "answer":   "I used to ride a bike to school",
                },
                "student_answer": "I am riding a bike to school",
                "unit": "Unit 1", "semester": 1,
            }
        )
        feedback = r.json().get("feedback", "")
        assert len(feedback) > 10, f"feedback 太短，没有解释原因：'{feedback}'"
        assert "used to" in feedback.lower() or "过去" in feedback, (
            f"feedback 没有指出关键语法点 used to：{feedback}"
        )

    def test_bug24_chinese_quotes_no_500(self, client, auth):
        """
        Bug#24：学生答案含中文双引号，不能返回 500。
        中文引号 " " 会破坏 JSON 序列化。
        """
        r = client.post("/api/quiz/grade",
            headers=auth,
            json={
                "question": {
                    "type":     "translation",
                    "question": "翻译：我过去常常骑车上学",
                    "answer":   "I used to ride a bike to school",
                },
                "student_answer": '我认为"I used to ride"这个答案是对的',
                "unit": "Unit 1", "semester": 1,
            }
        )
        assert r.status_code != 500, "Bug#24 未修复，中文引号导致 500"
        assert "is_correct" in r.json()


# ══════════════════════════════════════════════════════
# system prompt 行为规则验证
# ══════════════════════════════════════════════════════

class TestSystemPromptBehavior:

    def test_rejects_irrelevant_question(self, client, auth):
        """
        无关问题应该被礼貌拒绝。
        BASE_PROMPT 第2条：只回答与初中英语学习相关的问题
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "帮我写一段 Python 代码"}
        )
        content = r.json()["content"]
        # 不能直接写代码，应该说明只能回答英语问题
        assert "python" not in content.lower() or "英语" in content or "English" in content, (
            "Agent 没有拒绝无关问题，直接帮写代码了"
        )

    def test_rejects_out_of_scope_grammar(self, client, auth):
        """
        超纲问题应该说明超出范围，不能直接教。
        BASE_PROMPT：只回答八年级英语范围内的内容
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "高中英语虚拟语气完整用法，包括过去虚拟和现在虚拟"}
        )
        content = r.json()["content"]
        # 应该提到超出范围，不能大篇幅教虚拟语气
        out_of_scope_hints = ["超出", "范围", "八年级", "初中", "建议"]
        has_hint = any(hint in content for hint in out_of_scope_hints)
        # 如果没有提示，虚拟语气相关词汇也不应该出现大量
        assert has_hint or len(content) < 200, (
            "Agent 没有提示超纲，直接教了高中虚拟语气"
        )

    def test_friendly_tone_on_wrong_answer(self, client, auth):
        """
        批改错误答案时语气要友善鼓励。
        BASE_PROMPT 第3条：鼓励学生，语气友好亲切
        """
        r = client.post("/api/quiz/grade",
            headers=auth,
            json={
                "question": {
                    "type":     "translation",
                    "question": "翻译：我过去常常骑车上学",
                    "answer":   "I used to ride a bike to school",
                },
                "student_answer": "I am riding bike",
                "unit": "Unit 1", "semester": 1,
            }
        )
        feedback = r.json().get("feedback", "")
        # 不应该出现负面词汇
        negative_words = ["错误", "不对", "完全错", "根本不"]
        has_negative   = any(w in feedback for w in negative_words)
        # 应该有鼓励词汇
        encourage_words = ["继续", "加油", "不错", "努力", "再试", "注意", "记住"]
        has_encourage   = any(w in feedback for w in encourage_words)
        assert not has_negative or has_encourage, (
            f"批改语气不够友善：{feedback}"
        )

    def test_grammar_explanation_format(self, client, auth):
        """
        语法解释应包含：规则 + 例句 + 注意事项。
        GRAMMAR_ADDITION 模式要求三段式结构
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "used to 的语法规则"}
        )
        content = r.json()["content"]
        # 应该有例句（英文句子）
        assert "I used to" in content or "She used to" in content or "He used to" in content, (
            "语法解释里没有例句"
        )
        # 应该有中文解释
        assert any(c > '\u4e00' for c in content), "语法解释里没有中文说明"

    def test_quiz_generate_no_truncation(self, client):
        """
        Bug#23：生成 5 道题 JSON 不能截断。
        不需要认证（generate 接口无需 token）
        """
        r = client.post("/api/quiz/generate", json={
            "unit": "Unit 3", "semester": 1,
            "quiz_type": "multiple_choice",
            "count": 5,
            "difficulty": "medium"
        })
        assert r.status_code == 200, f"接口报错：{r.text}"
        data = r.json()
        assert "questions" in data, "JSON 解析失败，可能截断了"
        assert len(data["questions"]) >= 3, (
            f"只返回了 {len(data['questions'])} 道，可能 JSON 截断（Bug#23）"
        )
        # 每道题结构完整
        for q in data["questions"]:
            assert "question" in q
            assert "options"  in q
            assert "answer"   in q