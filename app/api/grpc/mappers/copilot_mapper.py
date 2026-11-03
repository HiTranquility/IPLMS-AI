"""Map message protobuf ↔ DTO Domain Copilot."""
from app.api.grpc.generated_stubs import get_stub
from app.core.copilot.dtos.copilot_dto import (
    AnswerChunk,
    AskQuestionRequest,
    CopilotAnswer,
    DisputeArbitrationRequest,
    DisputeVerdict,
    UsageSummary,
)

_pb2, _ = get_stub("copilot_service")


def to_ask_question_query(message) -> AskQuestionRequest:
    return AskQuestionRequest(
        query=message.query,
        user_id=message.user_id,
        user_role=message.user_role or "member",
        parking_lot_id=message.parking_lot_id or None,
        session_id=message.session_id or None,
        preview=message.preview,
    )


def to_arbitrate_dispute_command(message) -> DisputeArbitrationRequest:
    return DisputeArbitrationRequest(
        dispute_id=message.dispute_id,
        session_id=message.session_id,
        claim_reason=message.claim_reason,
        claimed_amount=message.claimed_amount,
    )


# Backward-compatible aliases
to_ask_question_request = to_ask_question_query
to_dispute_request = to_arbitrate_dispute_command


def to_ask_question_response(answer: CopilotAnswer):
    return _pb2.AskQuestionResponse(
        answer=answer.answer,
        sources=answer.sources,
        confidence=answer.confidence,
        model_revision=answer.model_revision,
        turn_id=answer.turn_id,
        prompt_version=answer.prompt_version,
    )


def to_answer_chunk(chunk: AnswerChunk):
    return _pb2.AnswerChunk(
        token=chunk.token,
        is_finished=chunk.is_finished,
        sources=chunk.sources,
        model_revision=chunk.model_revision,
        turn_id=chunk.turn_id,
        prompt_version=chunk.prompt_version,
    )


def to_arbitrate_dispute_response(verdict: DisputeVerdict):
    verdict_key = str(getattr(verdict.verdict, "value", verdict.verdict))
    proto_verdict = (
        _pb2.ArbitrationVerdict.ARBITRATION_VERDICT_UNSPECIFIED
        if verdict_key == "MANUAL_REVIEW"
        else _pb2.ArbitrationVerdict.Value(verdict_key)
    )
    return _pb2.ArbitrateDisputeResponse(
        verdict=proto_verdict,
        recommended_refund=verdict.recommended_refund,
        justification=verdict.justification,
        evidence_urls=verdict.evidence_urls,
    )


def to_feedback_command(message) -> tuple[str, str, int]:
    return message.turn_id, message.user_id, message.rating


def to_feedback_response(recorded: bool):
    return _pb2.RecordFeedbackResponse(recorded=recorded)


def to_usage_summary_response(summary: UsageSummary):
    return _pb2.UsageSummaryResponse(
        **summary.model_dump(exclude={"days", "avg_speed_tok_s"}),
        days=[
            _pb2.UsageDay(
                date=day.date,
                requests=day.requests,
                errors=day.errors,
                refused=day.refused,
                avg_latency_ms=day.avg_latency_ms,
            )
            for day in summary.days
        ],
    )
