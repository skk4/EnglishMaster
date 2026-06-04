"""
Global singleton services — loaded once at startup, reused across all requests.
Never instantiate these inside a request handler (would cost 10-60s per request).
"""
import logging
from dataclasses import dataclass

import torch
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from backend.config import get_settings
from backend.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()

_embedding_model: SentenceTransformer | None = None


@dataclass
class LLMClient:
    """Holds an LLM client + metadata so services don't need to know the provider."""
    client: OpenAI
    provider: str      # "minimax" | "openai"
    model: str         # "MiniMax-M3" | "gpt-4o-mini" | ...


_llm_client: LLMClient | None = None


async def startup_services():
    global _embedding_model, _llm_client

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[startup] Loading {settings.embedding_model} on {device.upper()}...")
    _embedding_model = SentenceTransformer(settings.embedding_model, device=device)
    print(f"[startup] ✅ Embedding model ready (dim=1024, device={device.upper()})")

    # 初始化 vector store（按 VECTOR_STORE_TYPE 自动选 Pinecone/FAISS/Qdrant/...）
    print(f"[startup] Connecting to vector store...")
    try:
        store = get_vector_store()
        stats = store.describe_stats()
        print(f"[startup] ✅ Vector store ready: {stats}")
    except Exception as e:
        logger.error(f"[startup] Vector store init failed: {e}")
        raise

    # 根据 LLM_PROVIDER 创建客户端
    provider = settings.llm_provider
    if provider == "openai":
        _llm_client = LLMClient(
            client=OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            ),
            provider="openai",
            model=settings.openai_model,
        )
    else:
        _llm_client = LLMClient(
            client=OpenAI(
                api_key=settings.minimax_api_key,
                base_url=settings.minimax_base_url,
            ),
            provider="minimax",
            model=settings.minimax_model,
        )
    print(f"[startup] ✅ LLM client ready (provider={_llm_client.provider}, model={_llm_client.model})")
    print("[startup] All services initialized.")


async def shutdown_services():
    global _embedding_model, _llm_client
    _embedding_model = None
    _llm_client = None


def get_embedding_model() -> SentenceTransformer:
    return _embedding_model


def get_vector_store_singleton():
    """获取当前激活的 vector store。"""
    return get_vector_store()


def get_llm_client() -> LLMClient:
    """Return the current LLM client + metadata (provider, model)."""
    return _llm_client
