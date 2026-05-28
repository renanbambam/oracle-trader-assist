"""Briefing endpoints — AI-generated morning briefing."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from oracle.application.briefing.dtos import BriefingOutput, GenerateBriefingInput
from oracle.application.briefing.generate_briefing import GenerateBriefingUseCase
from oracle.interface.api.dependencies import get_generate_briefing_use_case

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/morning", response_model=BriefingOutput)
async def morning_briefing(
    assets: list[str] = Query(default=["PETR4"], description="Assets to cover"),
    use_case: GenerateBriefingUseCase = Depends(get_generate_briefing_use_case),
) -> BriefingOutput:
    try:
        return await use_case.execute(GenerateBriefingInput(assets=assets))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
