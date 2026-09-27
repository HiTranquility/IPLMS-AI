"""Map protobuf KnowledgeEvalService ↔ dict của domain knowledge_eval."""
from typing import Any, Dict, List, Optional

from app.api.grpc.generated_stubs import get_stub

_pb2, _ = get_stub("knowledge_service")


def scope_of(message) -> Optional[str]:
    return message.parking_lot_id or None


def to_case_dict(message) -> Dict[str, Any]:
    return {
        "id": message.id or None,
        "parking_lot_id": message.parking_lot_id or None,
        "question": message.question,
        "expected_answer": message.expected_answer,
        "expected_facts": list(message.expected_facts),
        "expected_source": message.expected_source,
        "kind": message.kind,
        "created_by": message.created_by or "user",
    }


def to_case(case: Dict[str, Any]):
    return _pb2.TestCase(
        id=case.get("id") or "",
        parking_lot_id=case.get("parking_lot_id") or "",
        question=case["question"],
        expected_answer=case.get("expected_answer") or "",
        expected_facts=case.get("expected_facts") or [],
        expected_source=case.get("expected_source") or "",
        kind=case["kind"],
        created_by=case.get("created_by") or "user",
        author_id=case.get("author_id") or "",
        updated_at=case.get("updated_at") or "",
    )


def to_case_list(cases: List[Dict[str, Any]]):
    return _pb2.TestCaseList(cases=[to_case(c) for c in cases])


def to_run(run: Optional[Dict[str, Any]]):
    if not run:
        return _pb2.TestRun()
    return _pb2.TestRun(
        id=run["id"],
        parking_lot_id=run.get("parking_lot_id") or "",
        status=run["status"],
        total=run["total"],
        done=run["done"],
        passed=run["passed"],
        failed_facts=run["failed_facts"],
        failed_abstain=run["failed_abstain"],
        verdict_reasons=run.get("verdict_reasons") or [],
        error=run.get("error") or "",
        started_by=run.get("started_by") or "",
        started_at=run.get("started_at") or "",
        finished_at=run.get("finished_at") or "",
    )


def to_run_detail(detail: Dict[str, Any]):
    return _pb2.TestRunDetail(
        run=to_run(detail["run"]),
        results=[to_result(r) for r in detail["results"]],
    )


def to_result(r: Dict[str, Any]):
    return _pb2.TestResult(
        case_id=r["case_id"], question=r["question"], kind=r["kind"],
        expected_answer=r["expected_answer"], expected_facts=r["expected_facts"],
        answer=r["answer"], sources=r["sources"], passed=r["passed"],
        reasons=r["reasons"], reviewed=r.get("reviewed", False),
        approved=r.get("approved", False), review_note=r.get("review_note", ""),
        reviewed_by=r.get("reviewed_by", ""), reviewed_at=r.get("reviewed_at", ""),
        expected_source=r.get("expected_source", ""),
    )


def to_run_list(runs: List[Dict[str, Any]]):
    return _pb2.TestRunList(runs=[to_run(r) for r in runs])


def to_readiness(state: Dict[str, Any]):
    latest = state.get("latest_run")
    return _pb2.PublishReadiness(
        ready=state["ready"],
        reasons=state["reasons"],
        has_run=latest is not None,
        latest_run=to_run(latest),
        draft_count=state.get("draft_count", 0),
    )
