from fastapi import APIRouter, Query

from backend.services.vocab_service import (
    get_practice_words,
    get_unit_vocab,
    list_units,
)

router = APIRouter()


@router.get("/units")
async def units(semester: int = Query(1)):
    return {"semester": semester, "units": list_units(semester)}


@router.get("/unit")
async def unit_vocab(semester: int = Query(1), unit: str = Query("Unit 1")):
    return {"semester": semester, "unit": unit, "words": get_unit_vocab(semester, unit)}


@router.get("/practice")
async def practice(
    semester: int = Query(1),
    n: int = Query(10),
    units: str | None = Query(None),
):
    unit_list = [u.strip() for u in units.split(",")] if units else None
    words = get_practice_words(semester, n, unit_list)
    return {"semester": semester, "words": words}
