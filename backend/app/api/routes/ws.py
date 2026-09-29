"""WebSocket stream of live AI progress events for a ticket.

Browsers cannot set headers on WebSocket connections, so the JWT is passed as a `token`
query parameter. The server pushes new progress events as they are published and closes
the stream once the analysis completes or fails.
"""

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import user_from_token
from app.core.exceptions import AppError
from app.db.session import SessionFactory, get_session_factory
from app.models.enums import AIAnalysisStatus
from app.models.ticket import Ticket
from app.services.progress_service import get_progress
from app.services.ticket_service import is_staff

POLL_INTERVAL_SECONDS = 0.75
MAX_STREAM_SECONDS = 15 * 60

router = APIRouter(tags=["realtime"])


def _authorize(session_factory: SessionFactory, token: str, ticket_id: int) -> bool:
    with session_factory() as db:
        try:
            user = user_from_token(db, token)
        except AppError:
            return False
        return is_staff(user) and db.get(Ticket, ticket_id) is not None


def _analysis_status(session_factory: SessionFactory, ticket_id: int) -> AIAnalysisStatus | None:
    with session_factory() as db:
        ticket = db.get(Ticket, ticket_id)
        return ticket.ai_analysis_status if ticket else None


@router.websocket("/ws/tickets/{ticket_id}/ai-progress")
async def ai_progress_stream(
    websocket: WebSocket,
    ticket_id: int,
    session_factory: SessionFactory = Depends(get_session_factory),
) -> None:
    token = websocket.query_params.get("token", "")
    if not token or not await run_in_threadpool(_authorize, session_factory, token, ticket_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    sent = 0
    elapsed = 0.0
    try:
        while elapsed < MAX_STREAM_SECONDS:
            events = await run_in_threadpool(get_progress, ticket_id)
            for event in events[sent:]:
                await websocket.send_json({"type": "progress", **event})
            sent = max(sent, len(events))

            analysis_status = await run_in_threadpool(_analysis_status, session_factory, ticket_id)
            if analysis_status != AIAnalysisStatus.RUNNING:
                final_events = await run_in_threadpool(get_progress, ticket_id)
                for event in final_events[sent:]:
                    await websocket.send_json({"type": "progress", **event})
                await websocket.send_json({"type": "done", "status": analysis_status or "UNKNOWN"})
                break

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS
        await websocket.close()
    except WebSocketDisconnect:
        return
