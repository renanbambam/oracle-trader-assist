"""Replay endpoints — create session, advance frame, finish."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from oracle.application.replay.control_replay import ControlReplayUseCase
from oracle.application.replay.create_replay import CreateReplayUseCase
from oracle.application.replay.dtos import AnnotateFrameInput, AnnotateFrameOutput, CreateReplayInput, ReplayStatusOutput
from oracle.interface.api.dependencies import (
    get_annotate_frame_use_case,
    get_control_replay_use_case,
    get_create_replay_use_case,
)

router = APIRouter(prefix="/replay", tags=["replay"])


@router.post("", response_model=ReplayStatusOutput, status_code=status.HTTP_201_CREATED)
async def create_replay(
    body: CreateReplayInput,
    use_case: CreateReplayUseCase = Depends(get_create_replay_use_case),
) -> ReplayStatusOutput:
    try:
        return await use_case.execute(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.put("/{session_id}/next", response_model=ReplayStatusOutput)
async def next_frame(
    session_id: UUID,
    use_case: ControlReplayUseCase = Depends(get_control_replay_use_case),
) -> ReplayStatusOutput:
    try:
        return await use_case.next_frame(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{session_id}/annotate", response_model=AnnotateFrameOutput)
async def annotate_frame(
    session_id: UUID,
    body: AnnotateFrameInput,
    use_case=Depends(get_annotate_frame_use_case),
) -> AnnotateFrameOutput:
    try:
        return await use_case.execute(session_id, body)
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(exc)
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.put("/{session_id}/finish", response_model=ReplayStatusOutput)
async def finish_replay(
    session_id: UUID,
    use_case: ControlReplayUseCase = Depends(get_control_replay_use_case),
) -> ReplayStatusOutput:
    try:
        return await use_case.finish(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
