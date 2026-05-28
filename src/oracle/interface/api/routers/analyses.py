"""Analysis endpoints — trigger and retrieve chart analyses."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from oracle.application.analysis.dtos import RunAnalysisInput, RunAnalysisOutput
from oracle.application.analysis.run_analysis import RunAnalysisUseCase
from oracle.interface.api.dependencies import get_run_analysis_use_case

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=RunAnalysisOutput, status_code=status.HTTP_201_CREATED)
async def run_analysis(
    body: RunAnalysisInput,
    use_case: RunAnalysisUseCase = Depends(get_run_analysis_use_case),
) -> RunAnalysisOutput:
    try:
        return await use_case.execute(body)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=list[RunAnalysisOutput])
async def list_analyses(
    asset: str | None = Query(default=None, description="Filter by asset ticker"),
    limit: int = Query(default=20, ge=1, le=100),
    use_case: RunAnalysisUseCase = Depends(get_run_analysis_use_case),
) -> list[RunAnalysisOutput]:
    return await use_case.list_recent(asset=asset, limit=limit)


@router.get("/{analysis_id}", response_model=RunAnalysisOutput)
async def get_analysis(
    analysis_id: UUID,
    use_case: RunAnalysisUseCase = Depends(get_run_analysis_use_case),
) -> RunAnalysisOutput:
    result = await use_case.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return result
