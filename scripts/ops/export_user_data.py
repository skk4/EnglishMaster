#!/usr/bin/env python3
"""
导出用户数据（GDPR-like 权利）
用法：python scripts/ops/export_user_data.py --user-id 42
输出：./exports/user-42-{timestamp}.zip
包含：profile.json, chats.json, quiz_records.csv, vocab_progress.csv
"""
import argparse
import json
import zipfile
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from backend.models.db_models import AsyncSessionLocal, User, ChatSession, ChatMessage, QuizRecord, VocabProgress


async def export_user(user_id: int, output_path: Path):
    async with AsyncSessionLocal() as session:
        # 1. User profile
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")

        profile = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

        # 2. Chat sessions + messages
        sessions_result = await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at)
        )
        sessions = sessions_result.scalars().all()

        sessions_data = []
        for s in sessions:
            msgs_result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == s.id)
                .order_by(ChatMessage.id)
            )
            messages = msgs_result.scalars().all()
            sessions_data.append({
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "mode": m.mode,
                        "sources": json.loads(m.sources_json) if m.sources_json else [],
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in messages
                ],
            })

        # 3. Quiz records
        records_result = await session.execute(
            select(QuizRecord)
            .where(QuizRecord.user_id == user_id)
            .order_by(QuizRecord.created_at)
        )
        records = records_result.scalars().all()
        records_csv = io.StringIO()
        writer = csv.writer(records_csv)
        writer.writerow(["id", "unit", "semester", "quiz_type", "question", "student_answer", "correct_answer", "is_correct", "score", "created_at"])
        for r in records:
            writer.writerow([
                r.id, r.unit, r.semester, r.quiz_type, r.question_text,
                r.student_answer, r.correct_answer, r.is_correct, r.score,
                r.created_at.isoformat() if r.created_at else "",
            ])

        # 4. Vocab progress
        vocab_result = await session.execute(
            select(VocabProgress).where(VocabProgress.user_id == user_id)
        )
        vocab = vocab_result.scalars().all()
        vocab_csv = io.StringIO()
        writer = csv.writer(vocab_csv)
        writer.writerow(["word", "unit", "semester", "mastery_level", "review_count", "last_reviewed"])
        for v in vocab:
            writer.writerow([
                v.word, v.unit, v.semester, v.mastery_level, v.review_count,
                v.last_reviewed.isoformat() if v.last_reviewed else "",
            ])

    # 写 zip
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("profile.json", json.dumps(profile, ensure_ascii=False, indent=2))
        zf.writestr("chats.json", json.dumps(sessions_data, ensure_ascii=False, indent=2))
        zf.writestr("quiz_records.csv", records_csv.getvalue())
        zf.writestr("vocab_progress.csv", vocab_csv.getvalue())

    return {
        "user_id": user_id,
        "username": profile["username"],
        "sessions": len(sessions_data),
        "messages": sum(len(s["messages"]) for s in sessions_data),
        "quiz_records": len(records),
        "vocab_words": len(vocab),
        "output": str(output_path),
        "size_kb": round(output_path.stat().st_size / 1024, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--output-dir", default="./exports")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_path = Path(args.output_dir) / f"user-{args.user_id}-{timestamp}.zip"

    import asyncio
    summary = asyncio.run(export_user(args.user_id, output_path))

    print(f"✅ Exported user {summary['user_id']} ({summary['username']})")
    print(f"   Sessions:   {summary['sessions']} ({summary['messages']} messages)")
    print(f"   Quiz recs:  {summary['quiz_records']}")
    print(f"   Vocab:      {summary['vocab_words']} words")
    print(f"   File:       {summary['output']} ({summary['size_kb']} KB)")


if __name__ == "__main__":
    main()
