"""Handler gRPC cho KnowledgeEvalService (bộ test + cổng xuất bản, ISSUE-009)."""
from app.api.grpc.generated_stubs import get_stub
from app.api.grpc.mappers.knowledge_eval_mapper import (
    scope_of,
    to_case,
    to_case_dict,
    to_case_list,
    to_readiness,
    to_run,
    to_run_detail,
    to_run_list,
    to_result,
)
from app.core.knowledge_eval.services import knowledge_eval_service
from app.util.logger import logger

_pb2, _pb2_grpc = get_stub("knowledge_service")


class KnowledgeEvalHandler(_pb2_grpc.KnowledgeEvalServiceServicer):
    async def ListTestCases(self, request, context):
        return to_case_list(await knowledge_eval_service.list_cases(scope_of(request)))

    async def UpsertTestCase(self, request, context):
        case = await knowledge_eval_service.upsert_case(
            to_case_dict(request.test_case), request.actor_id
        )
        return to_case(case)

    async def DeleteTestCase(self, request, context):
        deleted = await knowledge_eval_service.delete_case(request.id, scope_of(request))
        return _pb2.DeleteTestCaseResponse(deleted=deleted)

    async def GenerateTestCases(self, request, context):
        logger.info("KnowledgeEval.GenerateTestCases lot_scoped=%s", bool(request.parking_lot_id))
        return to_case_list(
            await knowledge_eval_service.generate_cases(scope_of(request), request.max_cases)
        )

    async def StartTestRun(self, request, context):
        run = await knowledge_eval_service.start_run(
            scope_of(request), request.started_by, request.answer_profile_id or None
        )
        logger.info("KnowledgeEval.StartTestRun run=%s cases=%d", run["id"], run["total"])
        return to_run(run)

    async def GetTestRun(self, request, context):
        return to_run_detail(
            await knowledge_eval_service.get_run(request.run_id, scope_of(request))
        )

    async def ReviewTestResult(self, request, context):
        result = await knowledge_eval_service.review_result(
            request.run_id, request.case_id, scope_of(request),
            request.approved, request.note, request.reviewer_id,
        )
        return to_result(result)

    async def ListTestRuns(self, request, context):
        return to_run_list(await knowledge_eval_service.list_runs(scope_of(request)))

    async def GetPublishReadiness(self, request, context):
        return to_readiness(await knowledge_eval_service.readiness(scope_of(request)))

    async def PublishScope(self, request, context):
        count = await knowledge_eval_service.publish(scope_of(request), request.published_by)
        logger.info("KnowledgeEval.PublishScope published=%d", count)
        return _pb2.PublishScopeResponse(published_count=count)
