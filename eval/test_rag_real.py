"""
eval/test_rag_real.py — 真实 RAG 检索质量测试

测试目标：
  1. Pinecone 有没有被真正调用
  2. sources 字段内容对不对（unit / page_num / score）
  3. 课本内容能不能被检索到
  4. 超纲 / 无关问题 sources 是否为空或低分

运行：
    uvicorn backend.main:app --reload   # 先启动后端
    .venv/bin/python -m pytest eval/test_rag_real.py -v -s
"""
import pytest

pytestmark = pytest.mark.real


# ══════════════════════════════════════════════════════
# 第一类：sources 字段基本验证
# ══════════════════════════════════════════════════════

class TestSourcesField:

    def test_sources_not_empty_for_known_content(self, client, auth):
        """
        问课本里有的内容，sources 不能为空。
        sources 为空 = Pinecone 没工作，Claude 在靠自己回答。
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "used to 怎么用？"}
        )
        assert r.status_code == 200
        sources = r.json()["sources"]
        assert len(sources) > 0, (
            "sources 为空，RAG 没有工作。\n"
            "可能原因：Pinecone 连接失败 / 检索分数全低于阈值 / embedding 模型有问题"
        )

    def test_sources_score_above_threshold(self, client, auth):
        """检索分数应该 > 0.5，太低说明课本没索引好"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "比较级怎么构成？"}
        )
        sources = r.json()["sources"]
        assert len(sources) > 0, "sources 为空"
        best_score = max(s["score"] for s in sources)
        assert best_score > 0.5, (
            f"最高分 {best_score:.3f} 低于 0.5，检索质量差。\n"
            "建议：检查课本切片方式，或确认 embedding 模型是否匹配"
        )

    def test_sources_has_required_fields(self, client, auth):
        """sources 每条必须有 unit / section / page_num / score"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "outgoing 是什么意思？"}
        )
        sources = r.json()["sources"]
        assert len(sources) > 0, "sources 为空"
        for s in sources:
            assert "unit"     in s, f"缺少 unit：{s}"
            assert "score"    in s, f"缺少 score：{s}"
            assert "page_num" in s, f"缺少 page_num：{s}"
            assert "section"  in s, f"缺少 section：{s}"
            assert "semester" in s, f"缺少 semester：{s}"
            assert s["page_num"] > 0, f"page_num 不合法：{s['page_num']}"

    def test_sources_semester_field(self, client, auth):
        """semester 字段应该是 1 或 2"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "现在进行时怎么用？"}
        )
        sources = r.json()["sources"]
        assert len(sources) > 0, "sources 为空"
        for s in sources:
            assert s["semester"] in [1, 2], f"semester 值不合法：{s['semester']}"

    def test_filter_unit_sources_match(self, client, auth):
        """filter_unit 生效时，sources 里的 unit 应该匹配"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={
                "message": "这个单元的语法重点是什么？",
                "filter_unit": "Unit 1",
                "filter_semester": 1
            }
        )
        sources = r.json()["sources"]
        if sources:
            units = [s["unit"] for s in sources]
            assert any("Unit 1" in u for u in units), (
                f"filter_unit=Unit 1，但来源是：{units}"
            )


# ══════════════════════════════════════════════════════
# 第二类：RAG 陷阱测试
# 只有走了真实 RAG 才能答对的问题
# ══════════════════════════════════════════════════════

class TestRagTrap:

    def test_page_number_requires_rag(self, client, auth):
        """
        问具体页码 → 只有 RAG 才能回答。
        Claude 自己不知道"课本第几页"，答不出来 = 没走 RAG。
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "used to 这个语法点在课本第几页？"}
        )
        assert r.status_code == 200
        sources = r.json()["sources"]
        assert len(sources) > 0, "没走 RAG，无法回答页码问题"
        assert sources[0]["page_num"] > 0, "page_num 为 0，检索结果异常"

    def test_out_of_scope_low_score(self, client, auth):
        """
        超纲问题（高中虚拟语气）课本里没有，
        sources 应为空 或 最高分 < 0.6
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "高中英语虚拟语气完整用法是什么？"}
        )
        sources = r.json()["sources"]
        if sources:
            best_score = max(s["score"] for s in sources)
            assert best_score < 0.6, (
                f"超纲内容不应该有高分来源，实际最高分：{best_score:.3f}"
            )

    def test_irrelevant_question_no_high_score(self, client, auth):
        """完全无关的问题，sources 应为空或分数很低"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "今天上海天气怎么样？"}
        )
        assert r.status_code == 200
        sources = r.json()["sources"]
        if sources:
            best_score = max(s["score"] for s in sources)
            assert best_score < 0.4, (
                f"无关问题不应该检索到高分课本内容，实际：{best_score:.3f}"
            )

    def test_content_cites_unit_in_reply(self, client, auth):
        """
        回答里应该包含来源引用（Unit X），
        说明 LLM 真的用上了 RAG 检索到的内容，而不是忽略了。
        """
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": "used to 怎么用？"}
        )
        content = r.json()["content"]
        assert "Unit" in content or "unit" in content or "第" in content, (
            "回答里没有引用来源，LLM 可能忽略了 RAG 检索到的内容。\n"
            "建议：加强 system prompt 第5条'引用教材内容时注明来源'"
        )


# ══════════════════════════════════════════════════════
# 第三类：多单元路由测试
# 不同单元的问题，sources 应该对应正确的单元
# ══════════════════════════════════════════════════════

class TestUnitRouting:

    @pytest.mark.parametrize("question,expected_unit", [
        ("used to 的用法",       "Unit 1"),
        ("outgoing 是什么意思",  "Unit 3"),
        ("比较级的构成方式",      "Unit 3"),
    ])
    def test_unit_routing(self, client, auth, question, expected_unit):
        """问不同单元的问题，来源单元应该匹配"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={"message": question}
        )
        sources = r.json()["sources"]
        assert len(sources) > 0, f"'{question}' sources 为空"
        units = [s["unit"] for s in sources]
        assert any(expected_unit in u for u in units), (
            f"问题：{question}\n"
            f"期望来源包含：{expected_unit}\n"
            f"实际来源：{units}"
        )

    def test_semester_filter_works(self, client, auth):
        """上下册过滤正确"""
        r = client.post("/api/chat/sync",
            headers=auth,
            json={
                "message": "这学期的语法重点",
                "filter_semester": 2
            }
        )
        sources = r.json()["sources"]
        if sources:
            semesters = [s["semester"] for s in sources]
            assert all(s == 2 for s in semesters), (
                f"filter_semester=2，但来源包含：{semesters}"
            )