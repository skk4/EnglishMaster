#!/usr/bin/env python3
"""
性能基线测试

对每个核心 API 跑 100 次，记录 P50/P95/P99 延迟，对比上次基线。
CI 每周跑一次，差异 > 20% 触发告警。

用法：
    python scripts/ops/benchmark.py
    python scripts/ops/benchmark.py --base http://localhost:8000 --rounds 50
    python scripts/ops/benchmark.py --save-baseline  # 保存为新基线
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


DEFAULT_ENDPOINTS = [
    {"name": "health",        "method": "GET",  "path": "/api/health",               "auth": False},
    {"name": "auth_me",        "method": "GET",  "path": "/api/auth/me",               "auth": True},
    {"name": "vocab_practice", "method": "GET",  "path": "/api/vocab/practice?semester=1&n=5", "auth": True},
    {"name": "progress_summary", "method": "GET", "path": "/api/progress/summary",     "auth": True},
    {"name": "history_sessions", "method": "GET", "path": "/api/history/sessions",     "auth": True},
    # AI 接口很慢，单独测
    {"name": "chat_sync",     "method": "POST", "path": "/api/chat/sync",              "auth": True, "slow": True},
    {"name": "quiz_generate", "method": "POST", "path": "/api/quiz/generate",         "auth": True, "slow": True},
]


def register_and_get_token(base_url: str) -> str:
    """注册一个临时用户拿 token。"""
    username = f"bench_{int(time.time())}"
    password = "bench_pass_1234"
    with httpx.Client(base_url=base_url, timeout=10) as c:
        r = c.post("/api/auth/register", json={"username": username, "password": password})
        if r.status_code == 200:
            return r.json()["token"]
        # 已存在则登录
        r = c.post("/api/auth/login", json={"username": username, "password": password})
        return r.json()["token"]


def measure_one(c: httpx.Client, ep: dict, token: str | None) -> int:
    """跑一次，记录延迟（ms）。"""
    headers = {}
    if ep["auth"] and token:
        headers["Authorization"] = f"Bearer {token}"
    if ep["method"] == "POST":
        # 最小有效 body
        body = {"message": "test", "mode": "general"} if ep["path"] == "/api/chat/sync" else \
               {"unit": "Unit 1", "semester": 1, "quiz_type": "multiple_choice", "count": 1}
    else:
        body = None

    t0 = time.time()
    try:
        r = c.request(ep["method"], ep["path"], headers=headers, json=body)
        elapsed_ms = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            return -1
        return elapsed_ms
    except (httpx.TimeoutException, httpx.ConnectError):
        return -2  # 超时或连接错误


def percentiles(latencies: list[int], ps: list[int] = [50, 95, 99]) -> dict:
    if not latencies:
        return {f"p{p}": 0 for p in ps} | {"count": 0, "errors": 0}
    sorted_l = sorted(latencies)
    return {
        **{f"p{p}": sorted_l[min(len(sorted_l) - 1, int(len(sorted_l) * p / 100))] for p in ps},
        "min": min(latencies),
        "max": max(latencies),
        "avg": int(statistics.mean(latencies)),
        "count": len(latencies),
        "errors": 0,
    }


def run_benchmark(base_url: str, rounds: int, save_baseline: bool) -> dict:
    print(f"🔧 Benchmarking {base_url}, {rounds} rounds per endpoint...")
    token = register_and_get_token(base_url)
    print(f"   Token acquired: {token[:20]}...")

    results = {"timestamp": datetime.now(timezone.utc).isoformat(), "base_url": base_url, "rounds": rounds, "endpoints": {}}

    with httpx.Client(base_url=base_url, timeout=30) as c:
        for ep in DEFAULT_ENDPOINTS:
            # AI 接口只跑 5 轮（避免 token 耗尽和浪费时间）
            actual_rounds = min(rounds, 5) if ep.get("slow") else rounds
            print(f"  Testing {ep['name']:<20} ({actual_rounds} rounds)...", end="", flush=True)

            latencies = []
            errors = 0
            for i in range(actual_rounds):
                ms = measure_one(c, ep, token)
                if ms < 0:
                    errors += 1
                else:
                    latencies.append(ms)

            stats = percentiles(latencies)
            stats["errors"] = errors
            stats["rounds"] = actual_rounds
            results["endpoints"][ep["name"]] = stats
            print(f"  p50={stats['p50']}ms  p95={stats['p95']}ms  p99={stats['p99']}ms  errors={errors}")

    if save_baseline:
        baseline_path = Path("docs/PERFORMANCE_BASELINE.json")
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Baseline saved to {baseline_path}")

    return results


def compare_with_baseline(results: dict, baseline_path: Path, threshold_pct: float = 20.0) -> int:
    """对比基线，差异 > 20% 返回非 0（CI 失败）。"""
    if not baseline_path.exists():
        print(f"⚠ No baseline at {baseline_path}, skipping comparison")
        return 0

    with open(baseline_path) as f:
        baseline = json.load(f)

    print(f"\n📊 Comparison vs {baseline_path} (threshold ±{threshold_pct}%):")
    worst_degradation = 0.0
    for ep_name, current in results["endpoints"].items():
        if ep_name not in baseline.get("endpoints", {}):
            continue
        old = baseline["endpoints"][ep_name]
        old_p95 = old.get("p95", 1)
        new_p95 = current.get("p95", 1)
        if old_p95 == 0:
            continue
        delta_pct = (new_p95 - old_p95) / old_p95 * 100
        worst_degradation = max(worst_degradation, abs(delta_pct))
        sign = "+" if delta_pct > 0 else ""
        color = "\033[0;32m" if abs(delta_pct) < threshold_pct else "\033[0;31m"
        reset = "\033[0m"
        print(f"  {ep_name:<20}  p95: {old_p95}ms → {new_p95}ms  ({color}{sign}{delta_pct:.1f}%{reset})")

    if worst_degradation > threshold_pct:
        print(f"\n❌ Performance regression detected (max {worst_degradation:.1f}% > {threshold_pct}%)")
        return 1
    else:
        print(f"\n✅ Performance OK (max degradation {worst_degradation:.1f}% ≤ {threshold_pct}%)")
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("BENCHMARK_BASE", "http://localhost:8000"))
    parser.add_argument("--rounds", type=int, default=20, help="每端点轮数")
    parser.add_argument("--save-baseline", action="store_true", help="保存为新基线")
    parser.add_argument("--compare", action="store_true", help="对比基线")
    parser.add_argument("--threshold", type=float, default=20.0, help="退化阈值（百分比）")
    args = parser.parse_args()

    results = run_benchmark(args.base, args.rounds, args.save_baseline)

    if args.compare:
        baseline_path = Path("docs/PERFORMANCE_BASELINE.json")
        return compare_with_baseline(results, baseline_path, args.threshold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
