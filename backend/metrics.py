"""Prometheus metrics for LLM token tracking per user.

Labels on every metric: user_id, model, endpoint.

User-ID propagation uses a ContextVar (set by get_current_user dependency or
explicitly by unauthenticated routes).  Defaults to "anonymous".
"""

import contextvars
import time

from prometheus_client import Counter, Histogram

# ── User-ID context variable ──────────────────────────────────────
# Set inside get_current_user() dependency so every authenticated route
# automatically propagates the user ID to LLM call sites.
_current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user_id", default="anonymous"
)


def set_current_user_id(uid: str) -> None:
    _current_user_id.set(uid)


def get_current_user_id() -> str:
    return _current_user_id.get()


# ── Metric definitions ────────────────────────────────────────────
# Labels common to all LLM metrics:
#   user_id   – "1", "42", "anonymous"
#   provider  – "minimax" | "openai" | ...
#   model     – "MiniMax-M3" | "gpt-4o-mini" | ...
#   endpoint  – "chat_sync" | "chat_stream" | "quiz_generate" | "quiz_grade"

llm_input_tokens_total = Counter(
    "llm_input_tokens_total",
    "Total LLM input (prompt) tokens consumed",
    ["user_id", "provider", "model", "endpoint"],
)

llm_output_tokens_total = Counter(
    "llm_output_tokens_total",
    "Total LLM output (completion) tokens consumed",
    ["user_id", "provider", "model", "endpoint"],
)

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["user_id", "provider", "model", "endpoint", "status"],
)

# Buckets tilted toward LLM latency (sub-second fast path up to 60 s timeout)
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API request latency in seconds",
    ["user_id", "provider", "model", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0],
)


# ── Recording helper ──────────────────────────────────────────────

def record_llm_call(
    *,
    provider: str,
    model: str,
    endpoint: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    duration_s: float,
    status: str,  # "success" | "error"
) -> None:
    """Record a completed (or failed) LLM API call to Prometheus metrics."""
    uid = get_current_user_id()
    labels = {"user_id": uid, "provider": provider, "model": model, "endpoint": endpoint}

    llm_requests_total.labels(**labels, status=status).inc()
    llm_request_duration_seconds.labels(**labels).observe(duration_s)

    if status == "success":
        llm_input_tokens_total.labels(**labels).inc(input_tokens)
        llm_output_tokens_total.labels(**labels).inc(output_tokens)
