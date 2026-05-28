"""AnnotateFrameUseCase — requests Claude commentary on a replay frame."""

from uuid import UUID

from oracle.application.replay.dtos import AnnotateFrameInput, AnnotateFrameOutput
from oracle.core.ports import EventBus
from oracle.domain.replay.contracts import ReplayRepository
from prompts.replay.frame_annotation import build_prompt
from prompts.system.oracle_system_v1 import TEMPLATE as SYSTEM_PROMPT


class AnnotateFrameUseCase:
    """Calls Claude for a frame commentary and persists it to the replay session."""

    def __init__(
        self,
        replay_repo: ReplayRepository,
        ai_provider,   # AIProvider Protocol
        event_bus: EventBus,
    ) -> None:
        self._repo = replay_repo
        self._ai = ai_provider
        self._event_bus = event_bus

    async def execute(self, session_id: UUID, data: AnnotateFrameInput) -> AnnotateFrameOutput:
        session = await self._repo.get_by_id(session_id)
        if session is None:
            raise ValueError(f"Replay session {session_id} not found")

        frame_index = data.frame_index
        if frame_index >= len(session.frames):
            raise ValueError(f"Frame {frame_index} out of range (total={session.total_frames})")

        frame = session.frames[frame_index]
        annotations = [a.label for a in frame.annotations]

        prompt = build_prompt(
            asset=session.asset,
            timeframe=str(session.timeframe),
            frame_index=frame_index,
            timestamp=str(frame.timestamp),
            open=frame.bar.open,
            high=frame.bar.high,
            low=frame.bar.low,
            close=frame.bar.close,
            volume=frame.bar.volume,
            volume_context=frame.volume_context,
            annotations=annotations,
        )

        commentary = await self._ai.complete(prompt=prompt, system=SYSTEM_PROMPT)

        await self._repo.save_frame_annotation(session_id, frame_index, commentary)

        await self._event_bus.publish(
            channel="replay",
            event="replay.frame_annotated",
            payload={
                "session_id": str(session_id),
                "frame_index": frame_index,
                "asset": session.asset,
            },
        )

        return AnnotateFrameOutput(
            session_id=session_id,
            frame_index=frame_index,
            commentary=commentary,
        )
