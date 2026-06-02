from typing import Generator, Optional

from openai import OpenAI

from backend.config import get_settings
from backend.dependencies import get_chat_client
from backend.prompts.system_prompt import build_system_prompt
from backend.services.chat_history_service import strip_think_blocks
from backend.services.rag_service import RAGService

settings = get_settings()
MAX_HISTORY = 20  # keep last 10 turns (20 messages)


class AgentService:
    def __init__(self):
        self.client: OpenAI = get_chat_client()
        self.rag = RAGService()

    def _build_messages(self, system: str, user_message: str, history: list[dict]) -> list[dict]:
        messages = [{"role": "system", "content": system}]
        messages += history[-MAX_HISTORY:]
        messages.append({"role": "user", "content": user_message})
        return messages

    def _sources_from_chunks(self, chunks: list[dict]) -> list[dict]:
        return [
            {
                "unit":     c["unit"],
                "section":  c["section"],
                "page_num": c["page_num"],
                "semester": c["semester"],
                "score":    round(c["score"], 3),
            }
            for c in chunks
        ]

    def chat_sync(
        self,
        user_message: str,
        conversation_history: list[dict],
        mode: str = "general",
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> dict:
        chunks = self.rag.retrieve(
            user_message,
            filter_unit=filter_unit,
            filter_semester=filter_semester,
        )
        context = self.rag.format_context(chunks)
        system = build_system_prompt(mode=mode, context=context)
        messages = self._build_messages(system, user_message, conversation_history)

        response = self.client.chat.completions.create(
            model=settings.minimax_model,
            max_tokens=settings.max_tokens,
            messages=messages,
            extra_body={"thinking": {"type": "disabled"}},
        )

        return {
            "content": strip_think_blocks(response.choices[0].message.content),
            "usage": {
                "input_tokens":  response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            "sources": self._sources_from_chunks(chunks),
        }

    def chat_stream(
        self,
        user_message: str,
        conversation_history: list[dict],
        mode: str = "general",
        filter_unit: Optional[str] = None,
        filter_semester: Optional[int] = None,
    ) -> tuple[Generator[str, None, None], list[dict]]:
        chunks = self.rag.retrieve(
            user_message,
            filter_unit=filter_unit,
            filter_semester=filter_semester,
        )
        context = self.rag.format_context(chunks)
        system = build_system_prompt(mode=mode, context=context)
        messages = self._build_messages(system, user_message, conversation_history)

        stream = self.client.chat.completions.create(
            model=settings.minimax_model,
            max_tokens=settings.max_tokens,
            messages=messages,
            stream=True,
            extra_body={"thinking": {"type": "disabled"}},
        )

        def text_generator() -> Generator[str, None, None]:
            """
            流式输出时剥离 <think>...</think> 推理块。

            策略：
            - 累积 buffer
            - 见到完整 <think>...</think> 就丢弃中间内容
            - 见到残缺 <think>（没看到结尾）则暂存不输出，等下个 chunk
            - 见到残缺 </think>（没看到开头）则不输出，丢弃这一段
            - 正常内容原样 yield
            """
            buffer = ""
            in_think = False
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if not delta:
                    continue
                buffer += delta

                # 简单状态机
                while True:
                    if not in_think:
                        idx = buffer.find("<think>")
                        if idx == -1:
                            # 没 think 标签，输出全部
                            yield buffer
                            buffer = ""
                            break
                        # 输出 think 之前的内容
                        if idx > 0:
                            yield buffer[:idx]
                        buffer = buffer[idx + len("<think>"):]
                        in_think = True
                    else:
                        idx = buffer.find("</think>")
                        if idx == -1:
                            # 等下个 chunk
                            break
                        buffer = buffer[idx + len("</think>"):]
                        in_think = False

        return text_generator(), self._sources_from_chunks(chunks)
