"""
MiniMax M3 响应构造 + mock 工具

测试时用 MagicMock 替换真实 OpenAI 客户端，避免调真 API。
"""
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock


def make_chat_response(
    content: str,
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> MagicMock:
    """
    构造一个 MiniMax chat.completions.create 返回值。

    用法：
        mock = MagicMock()
        mock.chat.completions.create = AsyncMock(
            return_value=make_chat_response("hello")
        )
    """
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_response.choices[0].message.role = "assistant"
    mock_response.usage.prompt_tokens = prompt_tokens
    mock_response.usage.completion_tokens = completion_tokens
    return mock_response


def make_quiz_response(questions_json: str) -> MagicMock:
    """构造 quiz 生成的 mock（含 JSON 数组）。"""
    return make_chat_response(questions_json)


def make_grade_response(is_correct: bool, score: float = 1.0, feedback: str = "test") -> MagicMock:
    """构造 grade 批改的 mock。"""
    return make_chat_response(
        f'{{"is_correct": {str(is_correct).lower()}, "score": {score}, '
        f'"feedback": "{feedback}", "correction": ""}}'
    )


def make_streaming_response(chunks: list[str]) -> Any:
    """
    构造流式响应的 mock。chat_stream 协程迭代 .text_stream。
    注意：实际 chat.completions.create(stream=True) 返回的是 Stream 对象，
    不是 Response。简单 mock 起来复杂，所以这里返回普通 Response，
    让测试只覆盖 chat_sync。
    """
    raise NotImplementedError("流式 mock 太复杂，chat_sync 测试已覆盖核心逻辑")
