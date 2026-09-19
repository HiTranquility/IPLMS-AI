"""Map message protobuf ↔ DTO Domain Copilot."""
from app.api.grpc.generated_stubs import get_stub
from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
)

_pb2, _ = get_stub("copilot_service")


def to_ask_question_request(message) -> AskQuestionRequest:
    return AskQuestionRequest(
        query=message.query,
        user_id=message.user_id,
        user_role=message.user_role or "member",
        parking_lot_id=message.parking_lot_id or None,
        session_id=message.session_id or None,
    )


def to_dispute_request(message) -> DisputeArbitrationRequest:
    return DisputeArbitrationRequest(
        dispute_id=message.dispute_id,
        session_id=message.session_id,
        claim_reason=message.claim_reason,
        claimed_amount=message.claimed_amount,
    )


def to_ask_question_response(answer: CopilotAnswer):
    return _pb2.AskQuestionResponse(
        answer=answer.answer,
        sources=answer.sources,
        confidence=answer.confidence,
    )


def to_answer_chunk(chunk: AnswerChunk):
    return _pb2.AnswerChunk(
        token=chunk.token,
        is_finished=chunk.is_finished,
        sources=chunk.sources,
    )


def to_arbitrate_dispute_response(verdict: DisputeVerdict):
    return _pb2.ArbitrateDisputeResponse(
        verdict=_pb2.ArbitrationVerdict.Value(verdict.verdict),
        recommended_refund=verdict.recommended_refund,
        justification=verdict.justification,
        evidence_urls=verdict.evidence_urls,
    )
