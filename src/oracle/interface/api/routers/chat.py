"""Chat endpoints — fires streaming AI responses via WebSocket ai_stream channel."""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from oracle.application.analysis.send_message import SendMessageUseCase
from oracle.interface.api.dependencies import get_send_message_use_case

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("", status_code=202)
async def chat_stream(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    use_case: SendMessageUseCase = Depends(get_send_message_use_case),
) -> dict:
    """Start streaming a Claude response.

    Tokens are delivered to all WebSocket clients subscribed to the `ai_stream`
    channel as `ai.token` events. A final `ai.stream_end` event signals completion.
    The existing POST /analyses endpoint remains the synchronous fallback.
    """
    background_tasks.add_task(use_case.execute, body.message)
    return {"status": "streaming"}
