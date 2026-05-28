"""ControlReplayUseCase — advances and finishes replay sessions."""

from uuid import UUID

from oracle.application.replay.create_replay import replay_to_output
from oracle.application.replay.dtos import ReplayStatusOutput
from oracle.core.ports import EventBus
from oracle.domain.replay.enums import ReplayState
from oracle.domain.replay.events import ReplayCompleted, ReplayFrameAdvanced


class ControlReplayUseCase:
    def __init__(self, repository, event_bus: EventBus) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def next_frame(self, session_id: UUID) -> ReplayStatusOutput:
        session = await self._repo.get_by_id(session_id)
        if session is None:
            raise ValueError(f"Replay session {session_id} not found")
        if session.state == ReplayState.COMPLETED:
            return replay_to_output(session)

        new_frame = min(session.current_frame + 1, session.total_frames - 1)
        new_state = ReplayState.COMPLETED if new_frame >= session.total_frames - 1 else ReplayState.PLAYING

        await self._repo.update_state(session_id, new_state, new_frame, session.speed)
        session.current_frame = new_frame
        session.state = new_state

        frame_data = session.frames[new_frame] if session.frames else None
        if frame_data:
            await self._event_bus.publish(
                channel="replay",
                event="replay.frame_advanced",
                payload=ReplayFrameAdvanced(
                    replay_session_id=session_id,
                    frame_index=new_frame,
                    timestamp=frame_data.timestamp,
                    bar=frame_data.bar,
                ).model_dump(mode="json"),
            )

        if new_state == ReplayState.COMPLETED:
            await self._event_bus.publish(
                channel="replay",
                event="replay.completed",
                payload=ReplayCompleted(
                    replay_session_id=session_id,
                    total_frames_visited=new_frame + 1,
                ).model_dump(mode="json"),
            )

        return replay_to_output(session)

    async def finish(self, session_id: UUID) -> ReplayStatusOutput:
        session = await self._repo.get_by_id(session_id)
        if session is None:
            raise ValueError(f"Replay session {session_id} not found")

        await self._repo.update_state(
            session_id, ReplayState.COMPLETED,
            session.total_frames - 1, session.speed,
        )
        session.state = ReplayState.COMPLETED
        session.current_frame = session.total_frames - 1

        await self._event_bus.publish(
            channel="replay",
            event="replay.completed",
            payload=ReplayCompleted(
                replay_session_id=session_id,
                total_frames_visited=session.total_frames,
            ).model_dump(mode="json"),
        )

        return replay_to_output(session)
