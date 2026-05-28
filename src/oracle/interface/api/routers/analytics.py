"""Analytics endpoints — performance and summary reports."""

from fastapi import APIRouter, Depends

from oracle.application.analytics.dtos import PerformanceOutput, PerformanceQuery
from oracle.application.analytics.get_performance import GetPerformanceUseCase
from oracle.domain.analytics.enums import MetricPeriod
from oracle.interface.api.dependencies import get_performance_use_case

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/performance", response_model=PerformanceOutput)
async def get_performance(
    period: MetricPeriod = MetricPeriod.MONTHLY,
    asset: str | None = None,
    use_case: GetPerformanceUseCase = Depends(get_performance_use_case),
) -> PerformanceOutput:
    return await use_case.execute(PerformanceQuery(period=period, asset=asset))


@router.get("/summary", response_model=PerformanceOutput)
async def get_summary(
    use_case: GetPerformanceUseCase = Depends(get_performance_use_case),
) -> PerformanceOutput:
    return await use_case.get_summary()
