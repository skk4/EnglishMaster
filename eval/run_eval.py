"""
eval/run_eval.py — 一键跑所有上线前评测，输出报告

用法：
    uvicorn backend.main:app --reload        # 先启动后端
    .venv/bin/python eval/run_eval.py        # 跑全部
    .venv/bin/python eval/run_eval.py --only rag
    .venv/bin/python eval/run_eval.py --only quality
    .venv/bin/python eval/run_eval.py --only grading
    .venv/bin/python eval/run_eval.py --only behavior
"""
import sys
import subprocess
import argparse
from datetime import datetime

BASE_URL = "http://localhost:8000"


def check_server():
    import httpx
    try:
        return httpx.get(f"{BASE_URL}/api/health", timeout=5).status_code == 200
    except Exception:
        return False


def run_pytest(path, label):
    """跑 pytest，返回是否全部通过"""
    print(f"\n{'='*50}")
    print(f"▶  {label}")
    print(f"{'='*50}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-v", "--tb=short", "--no-header"],
        capture_output=False
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="EnglishMaster 上线前完整评测")
    parser.add_argument("--only",
        choices=["rag", "quality", "grading", "behavior"],
        help="只跑某一项"
    )
    args = parser.parse_args()

    print("\n" + "="*50)
    print("🎓  EnglishMaster Agent 上线前评测")
    print(f"    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    if not check_server():
        print("\n❌  服务器未启动，请先运行：")
        print("    uvicorn backend.main:app --reload")
        sys.exit(1)
    print("✅  服务器连接正常\n")

    results = {}

    if args.only in [None, "rag"]:
        results["RAG检索质量"] = run_pytest(
            "eval/test_rag_real.py",
            "RAG 检索质量测试（sources字段 / 单元路由 / 陷阱题）"
        )

    if args.only in [None, "quality", "grading", "behavior"]:
        # test_quality.py 包含三类：Ragas / 批改 / 行为规则
        target = "eval/test_quality.py"
        if args.only == "quality":
            target = "eval/test_quality.py::TestRagasQuality"
        elif args.only == "grading":
            target = "eval/test_quality.py::TestGradingAccuracy"
        elif args.only == "behavior":
            target = "eval/test_quality.py::TestSystemPromptBehavior"

        results["回答质量+批改+行为"] = run_pytest(
            target,
            "回答质量 / 批改准确性 / system prompt 行为规则"
        )

    # 最终汇总
    print("\n" + "="*50)
    print("📊  评测汇总")
    print("="*50)
    all_pass = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 未通过"
        print(f"  {status}  {name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("🎉  所有评测通过，可以上线！")
    else:
        print("⚠️   有评测未通过，建议修复后再上线。")
        print("     查看上方详细报错，定位具体问题。")
    print("="*50)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()