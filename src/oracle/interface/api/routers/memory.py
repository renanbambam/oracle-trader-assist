"""Memory endpoints — load context and expire sessions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oracle.application.memory.dtos import ContextOutput, LoadContextInput, SearchHistoryOutput
from oracle.application.memory.load_context import LoadContextUseCase
from oracle.application.memory.save_context import SaveContextUseCase
from oracle.interface.api.dependencies import (
    get_load_context_use_case,
    get_save_context_use_case,
    get_search_history_use_case,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/context", response_model=ContextOutput)
async def get_context(
    asset: str,
    create_if_missing: bool = True,
    use_case: LoadContextUseCase = Depends(get_load_context_use_case),
) -> ContextOutput:
    try:
        return await use_case.execute(LoadContextInput(asset=asset, create_if_missing=create_if_missing))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/search", response_model=SearchHistoryOutput)
async def search_history(
    asset: str,
    setup_type: str,
    limit: int = 5,
    use_case=Depends(get_search_history_use_case),
) -> SearchHistoryOutput:
    from oracle.application.memory.dtos import SearchHistoryInput
    return await use_case.execute(SearchHistoryInput(asset=asset, setup_type=setup_type, limit=limit))


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def expire_session(
    session_id: UUID,
    use_case: SaveContextUseCase = Depends(get_save_context_use_case),
) -> None:
    await use_case.expire(session_id)
