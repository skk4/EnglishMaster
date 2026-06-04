import json
import logging
import re
import time
from typing import Optional

from backend import metrics
from backend.dependencies import get_llm_client
from backend.prompts.quiz_prompt import GRADING_PROMPT, QUIZ_GENERATION_PROMPT
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


def parse_json_response(content: str) -> dict | list:
    content = content.strip()
    # Strip <think>...</think> reasoning block (MiniMax M3)
    if "<think>" in content:
        end = content.find("</think>")
        if end != -1:
            content = content[end + len("</think>"):].strip()
    # Replace CJK/fullwidth quotes (which break JSON parsing) with safe substitutes
    content = (
        content
        .replace("“", "«")   # left double quote → «
        .replace("”", "»")   # right double quote → »
        .replace("‘", "‹")   # left single  → ‹
        .replace("’", "›")   # right single → ›
        .replace("「", "《")
        .replace("」", "》")
    )
    # Strip markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Truncated JSON recovery:
    # Find every "}, " or "}\n" pattern (end of a complete object in an array),
    # try parsing progressively shorter prefixes. Most likely the AI output ends
    # mid-way through a JSON object; we want to keep all complete objects.
    candidates = []
    for opener, closer in [("[", "]"), ("{", "}")]:
        # Find all "}, " and "}," patterns
        idx = 0
        while True:
            j = content.find(closer, idx)
            if j == -1:
                break
            candidates.append((opener, closer, j))
            idx = j + 1

    # Sort by position (descending) — try longest first
    candidates.sort(key=lambda x: -x[2])

    for opener, closer, end_pos in candidates:
        start_pos = content.rfind(opener, 0, end_pos)
        if start_pos == -1:
            continue
        candidate = content[start_pos:end_pos + 1]
        # If array, ensure it has matching brackets
        if opener == "[":
            candidate = candidate + "]"
        else:
            candidate = candidate + "}"
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Last resort: try appending closers to balance
    for opener, closer in [("[", "]"), ("{", "}")]:
        start = content.find(opener)
        if start == -1:
            continue
        body = content[start:]
        # Strip trailing comma if any
        body = body.rstrip().rstrip(",")
        opens = body.count(opener) - body.count(closer)
        if opens > 0:
            try:
                return json.loads(body + closer * opens)
            except json.JSONDecodeError:
                pass

    logger.error(f"parse_json_response failed (len={len(content)}): {content[:500]}")
    raise ValueError(f"无法解析 AI 返回的 JSON (content length={len(content)})")


class QuizService:
    def __init__(self):
        llm = get_llm_client()
        self.client = llm.client
        self.provider = llm.provider
        self.model = llm.model
        self.rag = RAGService()

    def generate_quiz(
        self,
        unit: str,
        semester: int,
        quiz_type: str = "multiple_choice",
        count: int = 5,
        difficulty: str = "medium",
    ) -> list[dict]:
        """Generate quiz questions based on textbook content."""
        # RAG retrieve relevant content for this unit
        query = f"{unit} {quiz_type} 练习题 {difficulty}"
        chunks = self.rag.retrieve(
            query,
            top_k=2,
            filter_unit=unit,
            filter_semester=semester,
        )
        context = self.rag.format_context(chunks)

        prompt = QUIZ_GENERATION_PROMPT.format(
            context=context,
            count=count,
            quiz_type=quiz_type,
            difficulty=difficulty,
            unit=unit,
            semester=semester,
        )

        try:
            result = self._call_quiz_api(prompt, max_tokens=3000, strict=False)
        except ValueError:
            # Retry once with higher max_tokens (truncation, not length issue)
            result = self._call_quiz_api(prompt, max_tokens=6000, strict=True)
        if not isinstance(result, list):
            raise ValueError(f"Expected JSON array, got {type(result).__name__}")
        return result

    def _call_quiz_api(self, prompt: str, max_tokens: int, strict: bool) -> list:
        if strict:
            system = (
                "你是初中英语出题老师。极简输出：严格 JSON 数组，question≤30字，explanation≤15字。"
                "**禁止任何前缀文字**。"
            )
        else:
            system = (
                "你是初中英语出题老师。严格按 JSON 数组输出，**不要写 <think> 推理过程**。"
                "question 简短（< 50 字），explanation 简短（< 20 字）。"
            )
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                extra_body={"thinking": {"type": "disabled"}},
            )
            metrics.record_llm_call(
                provider=self.provider,
                model=self.model,
                endpoint="quiz_generate",
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                duration_s=time.time() - start,
                status="success",
            )
        except Exception:
            metrics.record_llm_call(
                provider=self.provider,
                model=self.model,
                endpoint="quiz_generate",
                duration_s=time.time() - start,
                status="error",
            )
            raise

        result = parse_json_response(response.choices[0].message.content)
        if not isinstance(result, list):
            raise ValueError(f"Expected JSON array, got {type(result).__name__}")
        return result

    def grade_answer(
        self,
        question: dict,
        student_answer: str,
    ) -> dict:
        """Grade a student's answer to a question."""
        if not student_answer or not student_answer.strip():
            return {
                "is_correct": False,
                "score": 0.0,
                "feedback": "未作答",
                "correction": f"正确答案：{question.get('answer', '')}",
            }

        # Fast path: exact match for multiple choice
        if question.get("type") == "multiple_choice":
            correct = question.get("answer", "").strip().upper()
            student = student_answer.strip().upper()
            if student == correct:
                return {
                    "is_correct": True,
                    "score": 1.0,
                    "feedback": "回答正确！",
                    "correction": "",
                }

        # Otherwise ask LLM to grade
        question_text = question.get("question", "")
        options = question.get("options", [])
        if options:
            question_text = f"{question_text}\n选项：\n" + "\n".join(options)

        prompt = GRADING_PROMPT.format(
            question_text=question_text,
            correct_answer=question.get("answer", ""),
            student_answer=student_answer,
        )

        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=600,
                messages=[
                    {"role": "system", "content": "你是初中英语老师，严格按 JSON 格式批改。**重要**：中文内容中**不要使用双引号**，用「」或省略。"},
                    {"role": "user", "content": prompt},
                ],
                extra_body={"thinking": {"type": "disabled"}},
            )
            # Record tokens immediately (API succeeded; parsing is an app concern)
            metrics.record_llm_call(
                provider=self.provider,
                model=self.model,
                endpoint="quiz_grade",
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                duration_s=time.time() - start,
                status="success",
            )
            return parse_json_response(response.choices[0].message.content)
        except (ValueError, json.JSONDecodeError):
            # LLM call succeeded but JSON was malformed — tokens already recorded.
            # Fallback: derive result from signal (correct answer vs student)
            correct = str(question.get("answer", "")).strip().upper()
            student = student_answer.strip().upper()
            is_correct = correct == student
            return {
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "feedback": "回答正确！" if is_correct else "回答错误。",
                "correction": f"正确答案：{question.get('answer', '')}",
            }
