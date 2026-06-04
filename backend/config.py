from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Provider 选择
    llm_provider: str = "minimax"  # minimax | openai

    # MiniMax API (OpenAI-compatible)
    minimax_api_key: str = ""
    minimax_model: str = "MiniMax-M3"
    minimax_base_url: str = "https://api.minimax.io/v1"

    # OpenAI API
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    max_tokens: int = 2048

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "xsjkndb01"
    pinecone_host: str = ""
    pinecone_environment: str = "us-east-1"

    # Embedding
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dimension: int = 1024

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    database_url: str = "sqlite+aiosqlite:///./database/app.db"
    max_context_chunks: int = 5
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
