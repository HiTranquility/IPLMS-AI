"""Handler gRPC cho CopilotService (RAG hỏi đáp, streaming token, phân xử tranh chấp)."""
from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.copilot_mapper import (
    to_answer_chunk,
    to_arbitrate_dispute_response,
    to_ask_question_request,
    to_ask_question_response,
    to_dispute_request,
)
from app.core.copilot.services.copilot_service import copilot_service
from app.utils.logger import logger

_, _pb2_grpc = get_stub("copilot_service")


class CopilotHandler(_pb2_grpc.CopilotServiceServicer):
    async def AskQuestion(self, request, context):
        payload = to_ask_question_request(request)
        logger.info("CopilotService.AskQuestion query_chars=%d", len(payload.query))
        return to_ask_question_response(await copilot_service.ask_question(payload))

    async def StreamAnswer(self, request, context):
        payload = to_ask_question_request(request)
        logger.info("CopilotService.StreamAnswer query_chars=%d", len(payload.query))
        async for chunk in copilot_service.stream_answer(payload):
            yield to_answer_chunk(chunk)

    async def ArbitrateDispute(self, request, context):
        payload = to_dispute_request(request)
        logger.info(f"CopilotService.ArbitrateDispute dispute={payload.dispute_id}")
        return to_arbitrate_dispute_response(await copilot_service.arbitrate_dispute(payload))
