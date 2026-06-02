from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db_models import AsyncSessionLocal, QuizRecord, VocabProgress


async def save_quiz_record(
    user_id: int,
    unit: str,
    semester: int,
    quiz_type: str,
    question_text: str,
    student_answer: str,
    correct_answer: str,
    is_correct: bool,
    score: float,
) -> int:
    async with AsyncSessionLocal() as session:
        record = QuizRecord(
            user_id=user_id,
            unit=unit,
            semester=semester,
            quiz_type=quiz_type,
            question_text=question_text,
            student_answer=student_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            score=score,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record.id


async def get_progress_summary(user_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizRecord).where(QuizRecord.user_id == user_id)
        )
        records = result.scalars().all()

        if not records:
            return {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
                "avg_score": 0.0,
                "weak_units": [],
            }

        total = len(records)
        correct = sum(1 for r in records if r.is_correct)
        avg_score = sum(r.score for r in records) / total

        unit_stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0})
        for r in records:
            key = f"s{r.semester} {r.unit}"
            unit_stats[key]["total"] += 1
            if r.is_correct:
                unit_stats[key]["correct"] += 1

        weak_units = sorted(
            [
                {
                    "unit":     k,
                    "total":    v["total"],
                    "correct":  v["correct"],
                    "accuracy": round(v["correct"] / v["total"], 3) if v["total"] else 0.0,
                }
                for k, v in unit_stats.items()
            ],
            key=lambda x: x["accuracy"],
        )[:3]

        return {
            "total":      total,
            "correct":    correct,
            "accuracy":   round(correct / total, 3),
            "avg_score":  round(avg_score, 3),
            "weak_units": weak_units,
        }


async def get_recent_records(user_id: int, limit: int = 20) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QuizRecord)
            .where(QuizRecord.user_id == user_id)
            .order_by(desc(QuizRecord.created_at))
            .limit(limit)
        )
        records = result.scalars().all()
        return [
            {
                "id":             r.id,
                "unit":           r.unit,
                "semester":       r.semester,
                "quiz_type":      r.quiz_type,
                "question":       r.question_text,
                "student_answer": r.student_answer,
                "is_correct":     r.is_correct,
                "score":          round(r.score, 3),
                "created_at":     r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]


async def update_vocab_progress(
    user_id: int, word: str, unit: str, semester: int, mastered: bool
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(VocabProgress).where(
                VocabProgress.user_id == user_id,
                VocabProgress.word == word,
                VocabProgress.unit == unit,
                VocabProgress.semester == semester,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = VocabProgress(
                user_id=user_id, word=word, unit=unit, semester=semester,
                mastery_level=1 if mastered else 0,
                review_count=1,
                last_reviewed=datetime.now(timezone.utc),
            )
            session.add(record)
        else:
            record.review_count += 1
            if mastered:
                record.mastery_level = min(record.mastery_level + 1, 3)
            else:
                record.mastery_level = max(record.mastery_level - 1, 0)
            record.last_reviewed = datetime.now(timezone.utc)
        await session.commit()
