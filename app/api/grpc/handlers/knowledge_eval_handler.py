"""Handler gRPC cho KnowledgeEvalService (bộ test + cổng xuất bản, ISSUE-009)."""
from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.knowledge_eval_mapper import (
    to_case_list_response,
    to_case_response,
    to_create_case_command,
    to_eval_scope_query,
    to_readiness_response,
    to_result_response,
    to_run_detail_response,
    to_run_list_response,
    to_run_response,
)
from app.core.knowledge_eval import eval_service
from app.util.logger import logger

_pb2, _pb2_grpc = get_stub("knowledge_service")


class KnowledgeEvalHandler(_pb2_grpc.KnowledgeEvalServiceServicer):
    async def ListTestCases(self, request, context):
        return to_case_list_response(
            await eval_service.list_cases(to_eval_scope_query(request))
        )

    async def UpsertTestCase(self, request, context):
        case = await eval_service.upsert_case(
            to_create_case_command(request.test_case), request.actor_id
        )
        return to_case_response(case)

    async def DeleteTestCase(self, request, context):
        deleted = await eval_service.delete_case(
            request.id, to_eval_scope_query(request)
        )
        return _pb2.DeleteTestCaseResponse(deleted=deleted)

    async def GenerateTestCases(self, request, context):
        logger.info("KnowledgeEval.GenerateTestCases lot_scoped=%s", bool(request.parking_lot_id))
        return to_case_list_response(
            await eval_service.generate_cases(
                to_eval_scope_query(request), request.max_cases
            )
        )

    async def StartTestRun(self, request, context):
        run = await eval_service.start_run(
            to_eval_scope_query(request), request.started_by, request.answer_profile_id or None
        )
        logger.info("KnowledgeEval.StartTestRun run=%s cases=%d", run["id"], run["total"])
        return to_run_response(run)

    async def GetTestRun(self, request, context):
        return to_run_detail_response(
            await eval_service.get_run(request.run_id, to_eval_scope_query(request))
        )

    async def ReviewTestResult(self, request, context):
        result = await eval_service.review_result(
            request.run_id, request.case_id, to_eval_scope_query(request),
            request.approved, request.note, request.reviewer_id,
        )
        return to_result_response(result)

    async def ListTestRuns(self, request, context):
        return to_run_list_response(
            await eval_service.list_runs(to_eval_scope_query(request))
        )

    async def GetPublishReadiness(self, request, context):
        return to_readiness_response(
            await eval_service.readiness(to_eval_scope_query(request))
        )

    async def PublishScope(self, request, context):
        count = await eval_service.publish(
            to_eval_scope_query(request), request.published_by
        )
        logger.info("KnowledgeEval.PublishScope published=%d", count)
        return _pb2.PublishScopeResponse(published_count=count)
