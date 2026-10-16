"""Local diagnostic adapter to the guarded production Copilot service."""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from app.api.rest.developer_access import limit_developer_calls
from app.api.rest.schemas.base_response import BaseResponse
from app.core.copilot.dtos.copilot_dto import AskQuestionRequest, CopilotAnswer
from app.core.copilot.services.copilot_service import copilot_service

router = APIRouter(prefix="/copilot", tags=["Developer Copilot"],
                   dependencies=[Depends(limit_developer_calls)])


class AskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    parking_lot_id: Optional[str] = Field(None, max_length=128)


@router.post("/ask", response_model=BaseResponse[CopilotAnswer])
async def ask_copilot(payload: AskPayload) -> BaseResponse[CopilotAnswer]:
    answer = await copilot_service.ask_question(AskQuestionRequest(
        query=payload.query, parking_lot_id=payload.parking_lot_id,
        user_id="local-developer", preview=False,
    ))
    return BaseResponse.ok([answer], "Answer from guarded RAG pipeline")
