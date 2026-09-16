from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from qa_api.dependencies import get_ask_service
from qa_api.schemas import AskRequest, AskResponse
from qa_api.service import AskQuestion

router = APIRouter()


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.post("/api/v1/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    service: Annotated[AskQuestion, Depends(get_ask_service)],
) -> AskResponse:
    return await service.execute(request)
