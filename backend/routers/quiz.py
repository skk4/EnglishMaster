from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.routers.auth import get_current_user
from backend.services.quiz_service import QuizService
from backend.services.progress_service import save_quiz_record

router = APIRouter()


class GenerateRequest(BaseModel):
    unit: str
    semester: int
    quiz_type: str = "multiple_choice"
    count: int = 5
    difficulty: str = "medium"


class GradeRequest(BaseModel):
    question: dict
    student_answer: str
    unit: str = "Unit 1"
    semester: int = 1


@router.post("/generate")
async def generate_quiz(request: GenerateRequest):
    """Generate quiz questions based on textbook content."""
    if request.count > 20:
        raise HTTPException(status_code=400, detail="count must be <= 20")
    if request.quiz_type not in ("multiple_choice", "fill_blank", "translation"):
        raise HTTPException(
            status_code=400,
            detail="quiz_type must be: multiple_choice | fill_blank | translation",
        )

    service = QuizService()
    questions = service.generate_quiz(
        unit=request.unit,
        semester=request.semester,
        quiz_type=request.quiz_type,
        count=request.count,
        difficulty=request.difficulty,
    )
    return {"questions": questions}


@router.post("/grade")
async def grade_answer(request: GradeRequest, user: dict = Depends(get_current_user)):
    """Grade a student's answer and save to progress log."""
    service = QuizService()
    result = service.grade_answer(request.question, request.student_answer)

    # Save to progress log (scoped to current user)
    await save_quiz_record(
        user_id=user["id"],
        unit=request.unit,
        semester=request.semester,
        quiz_type=request.question.get("type", "unknown"),
        question_text=request.question.get("question", ""),
        student_answer=request.student_answer,
        correct_answer=request.question.get("answer", ""),
        is_correct=result.get("is_correct", False),
        score=result.get("score", 0.0),
    )

    return result
