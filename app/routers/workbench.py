from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.routers.word import get_db
from app.schemas.workbench_schema import (
    LineReadingChoiceResponse,
    LineReadingSlotResponse,
    LineReadingsRequest,
    ReplacementPlanV1,
    WorkbenchCandidateResponse,
)
from app.services.workbench.line_readings import resolve_line_readings
from app.services.workbench.replacement_planner import plan_replacements
from app.startup.readiness_gate import require_search_ready


router = APIRouter(prefix="/workbench", tags=["workbench"])


@router.post("/readings", response_model=list[LineReadingSlotResponse])
def workbench_readings(
    body: LineReadingsRequest,
    db: Session = Depends(get_db),
) -> list[LineReadingSlotResponse]:
    require_search_ready()
    return [
        LineReadingSlotResponse(
            surface=slot.surface,
            kind=slot.kind,
            choices=[LineReadingChoiceResponse(**choice.__dict__) for choice in slot.choices],
            needs_choice=slot.needs_choice,
        )
        for slot in resolve_line_readings(body.surface, db)
    ]


@router.post("/candidates", response_model=WorkbenchCandidateResponse)
def workbench_candidates(
    body: ReplacementPlanV1,
    db: Session = Depends(get_db),
) -> WorkbenchCandidateResponse:
    require_search_ready()
    return plan_replacements(body, db)


__all__ = ["router"]
