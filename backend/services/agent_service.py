import time
from typing import Generator, Optional

from backend import metrics
from backend.config import get_settings
from backend.dependencies import get_llm_client
from backend.prompts.system_prompt import build_system_prompt
from backend.services.chat_history_service import strip_think_blocks
from backend.services.rag_service import RAGService

settings = get_settings()
MAX_HISTORY = 20  # keep last 10 turns (20 messages)


class AgentService:
    def __init__(self):
        llm = get_llm_client()
        self.client = llm.client
        self.provider = llm.provider
        self.model = llm.model
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

        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=settings.max_tokens,
                messages=messages,
                extra_body={"thinking": {"type": "disabled"}},
            )
            metrics.record_llm_call(
                provider=self.provider,
                model=self.model,
                endpoint="chat_sync",
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                duration_s=time.time() - start,
                status="success",
            )
        except Exception:
            metrics.record_llm_call(
                provider=self.provider,
                model=self.model,
                endpoint="chat_sync",
                duration_s=time.time() - start,
                status="error",
            )
            raise

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

        # Estimate input tokens from prompt length (streaming doesn't return usage)
        # Mixed Chinese-English: ~2.5 chars per token
        input_chars = sum(len(m["content"]) for m in messages)
        estimated_input_tokens = max(1, int(input_chars / 2.5))

        start = time.time()
        stream = self.client.chat.completions.create(
            model=self.model,
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
            output_chars = 0  # accumulate for token estimation
            try:
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
                                output_chars += len(buffer)
                                buffer = ""
                                break
                            # 输出 think 之前的内容
                            if idx > 0:
                                yield buffer[:idx]
                                output_chars += idx
                            buffer = buffer[idx + len("<think>"):]
                            in_think = True
                        else:
                            idx = buffer.find("</think>")
                            if idx == -1:
                                # 等下个 chunk
                                break
                            buffer = buffer[idx + len("</think>"):]
                            in_think = False

                # Stream fully consumed — record estimated token counts
                # English-heavy output: ~2 chars per token
                estimated_output_tokens = max(1, int(output_chars / 2.0))
                metrics.record_llm_call(
                    provider=self.provider,
                    model=self.model,
                    endpoint="chat_stream",
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens,
                    duration_s=time.time() - start,
                    status="success",
                )
            except Exception:
                metrics.record_llm_call(
                    provider=self.provider,
                    model=self.model,
                    endpoint="chat_stream",
                    duration_s=time.time() - start,
                    status="error",
                )
                raise

        return text_generator(), self._sources_from_chunks(chunks)
