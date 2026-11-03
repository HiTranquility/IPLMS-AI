"""Map protobuf KnowledgeEvalService ↔ DTO/dict của domain knowledge_eval."""
from typing import Any, Dict, List, Mapping, Optional

from app.api.grpc.generated_stubs import get_stub
from app.core.knowledge_eval.dtos import (
    EvalScopeDto,
    ScopeReadinessDto,
    TestCaseDto,
    TestRunResultDto,
    TestRunSummaryDto,
)

_pb2, _ = get_stub("knowledge_service")


def to_eval_scope_query(message) -> Optional[str]:
    return EvalScopeDto(parking_lot_id=message.parking_lot_id or None).parking_lot_id


def to_create_case_command(message) -> Dict[str, Any]:
    dto = TestCaseDto(
        id=message.id or None,
        parking_lot_id=message.parking_lot_id or None,
        question=message.question,
        expected_answer=message.expected_answer,
        expected_facts=list(message.expected_facts),
        expected_source=message.expected_source,
        kind=message.kind,
        created_by=message.created_by or "user",
    )
    return dto.to_dict()


def to_case_response(case: Mapping[str, Any] | TestCaseDto):
    dto = TestCaseDto.from_dict(case)
    return _pb2.TestCase(
        id=dto.id or "",
        parking_lot_id=dto.parking_lot_id or "",
        question=dto.question,
        expected_answer=dto.expected_answer or "",
        expected_facts=dto.expected_facts or [],
        expected_source=dto.expected_source or "",
        kind=dto.kind,
        created_by=dto.created_by or "user",
        author_id=dto.author_id or "",
        updated_at=dto.updated_at or "",
    )


def to_case_list_response(cases: List[Dict[str, Any]]):
    return _pb2.TestCaseList(cases=[to_case_response(c) for c in cases])


def to_run_response(run: Optional[Mapping[str, Any] | TestRunSummaryDto]):
    if not run:
        return _pb2.TestRun()
    dto = TestRunSummaryDto.from_dict(run)
    return _pb2.TestRun(
        id=dto.id,
        parking_lot_id=dto.parking_lot_id or "",
        status=dto.status,
        total=dto.total,
        done=dto.done,
        passed=dto.passed,
        failed_facts=dto.failed_facts,
        failed_abstain=dto.failed_abstain,
        verdict_reasons=dto.verdict_reasons or [],
        error=dto.error or "",
        started_by=dto.started_by or "",
        started_at=dto.started_at or "",
        finished_at=dto.finished_at or "",
        answer_profile_id=dto.answer_profile_id or "",
        judge_profile_id=dto.judge_profile_id or "",
    )


def to_run_detail_response(detail: Mapping[str, Any]):
    return _pb2.TestRunDetail(
        run=to_run_response(detail["run"]),
        results=[to_result_response(r) for r in detail["results"]],
    )


def to_result_response(r: Mapping[str, Any] | TestRunResultDto):
    dto = TestRunResultDto.from_dict(r)
    return _pb2.TestResult(
        case_id=dto.case_id,
        question=dto.question,
        kind=dto.kind,
        expected_answer=dto.expected_answer,
        expected_facts=dto.expected_facts,
        answer=dto.answer,
        sources=dto.sources,
        passed=dto.passed,
        reasons=dto.reasons,
        reviewed=dto.reviewed,
        approved=dto.approved,
        review_note=dto.review_note,
        reviewed_by=dto.reviewed_by,
        reviewed_at=dto.reviewed_at,
        expected_source=dto.expected_source,
    )


def to_run_list_response(runs: List[Dict[str, Any]]):
    return _pb2.TestRunList(runs=[to_run_response(r) for r in runs])


def to_readiness_response(state: Mapping[str, Any] | ScopeReadinessDto):
    dto = ScopeReadinessDto.from_dict(state)
    latest = dto.latest_run
    return _pb2.PublishReadiness(
        ready=dto.ready,
        reasons=dto.reasons,
        has_run=latest is not None,
        latest_run=to_run_response(latest),
        draft_count=dto.draft_count,
    )


# Backward-compatible aliases
scope_of = to_eval_scope_query
to_case_dict = to_create_case_command
to_case = to_case_response
to_case_list = to_case_list_response
to_run = to_run_response
to_run_detail = to_run_detail_response
to_result = to_result_response
to_run_list = to_run_list_response
to_readiness = to_readiness_response
