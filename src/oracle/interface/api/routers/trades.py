"""Trade endpoints — record, list and close trades."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oracle.application.trade.close_trade import CloseTradeUseCase
from oracle.application.trade.dtos import (
    ChecklistInput,
    ChecklistOutput,
    CloseTradeInput,
    RecordTradeInput,
    ReflectionOutput,
    TradeOutput,
)
from oracle.application.trade.record_trade import RecordTradeUseCase
from oracle.interface.api.dependencies import (
    get_checklist_use_case,
    get_close_trade_use_case,
    get_record_trade_use_case,
    get_reflect_use_case,
)

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("", response_model=TradeOutput, status_code=status.HTTP_201_CREATED)
async def record_trade(
    body: RecordTradeInput,
    use_case: RecordTradeUseCase = Depends(get_record_trade_use_case),
) -> TradeOutput:
    try:
        return await use_case.execute(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=list[TradeOutput])
async def list_trades(
    limit: int = 50,
    use_case: RecordTradeUseCase = Depends(get_record_trade_use_case),
) -> list[TradeOutput]:
    return await use_case.list_recent(limit=limit)


@router.post("/checklist", response_model=ChecklistOutput)
async def run_checklist(
    body: ChecklistInput,
    use_case=Depends(get_checklist_use_case),
) -> ChecklistOutput:
    return use_case.execute(body)


@router.post("/{trade_id}/reflect", response_model=ReflectionOutput)
async def reflect_on_trade(
    trade_id: UUID,
    use_case=Depends(get_reflect_use_case),
) -> ReflectionOutput:
    try:
        return await use_case.execute(trade_id)
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(exc)
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.put("/{trade_id}/close", response_model=TradeOutput)
async def close_trade(
    trade_id: UUID,
    body: CloseTradeInput,
    use_case: CloseTradeUseCase = Depends(get_close_trade_use_case),
) -> TradeOutput:
    if body.trade_id != trade_id:
        body = body.model_copy(update={"trade_id": trade_id})
    try:
        return await use_case.execute(body)
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(exc)
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=str(exc))
