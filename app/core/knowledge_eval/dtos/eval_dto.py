"""DTO cho domain Knowledge Eval — bộ test & cổng xuất bản kho tri thức (ISSUE-009)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Iterator, List, Mapping, Optional


class _DictCompatibleDto:
    """Cho phép truy cập kiểu thuộc tính lẫn kiểu dict (`dto["k"]`, `dto.get("k")`, `{**dto}`)."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)  # type: ignore[arg-type]

    def keys(self) -> List[str]:
        return [f.name for f in fields(self)]  # type: ignore[arg-type]

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.keys())

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
            return
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def items(self):
        return [(k, getattr(self, k)) for k in self.keys()]

    def values(self):
        return [getattr(self, k) for k in self.keys()]


@dataclass
class EvalScopeDto(_DictCompatibleDto):
    """Phạm vi kho tri thức (`None` = tài liệu chung toàn hệ thống)."""

    parking_lot_id: Optional[str] = None

    @classmethod
    def from_raw(cls, scope: Optional[str] | "EvalScopeDto" | Mapping[str, Any]) -> "EvalScopeDto":
        if isinstance(scope, cls):
            return scope
        if isinstance(scope, Mapping):
            raw = scope.get("parking_lot_id")
            return cls(parking_lot_id=str(raw).strip() or None if raw else None)
        return cls(parking_lot_id=str(scope).strip() or None if scope else None)


@dataclass
class TestCaseDto(_DictCompatibleDto):
    """Một câu hỏi kiểm thử trong bộ test Knowledge Base."""

    question: str
    kind: str = "fact"
    id: Optional[str] = None
    parking_lot_id: Optional[str] = None
    expected_answer: str = ""
    expected_facts: List[str] = field(default_factory=list)
    expected_source: str = ""
    created_by: str = "user"
    author_id: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TestCaseDto":
        if isinstance(data, cls):
            return data
        return cls(
            id=data.get("id") or None,
            parking_lot_id=data.get("parking_lot_id") or None,
            question=str(data.get("question") or ""),
            expected_answer=str(data.get("expected_answer") or ""),
            expected_facts=list(data.get("expected_facts") or []),
            expected_source=str(data.get("expected_source") or ""),
            kind=str(data.get("kind") or "fact"),
            created_by=str(data.get("created_by") or "user"),
            author_id=str(data.get("author_id") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class TestRunSummaryDto(_DictCompatibleDto):
    """Tóm tắt một lượt chạy bộ test Knowledge Base."""

    id: str
    status: str = "RUNNING"
    parking_lot_id: Optional[str] = None
    total: int = 0
    done: int = 0
    passed: int = 0
    failed_facts: int = 0
    failed_abstain: int = 0
    verdict_reasons: List[str] = field(default_factory=list)
    error: str = ""
    started_by: str = ""
    started_at: str = ""
    finished_at: str = ""
    answer_profile_id: str = ""
    judge_profile_id: str = ""
    version_ids: List[str] = field(default_factory=list)
    docs_fingerprint: str = ""
    suite_fingerprint: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TestRunSummaryDto":
        if isinstance(data, cls):
            return data
        return cls(
            id=str(data["id"]),
            parking_lot_id=data.get("parking_lot_id") or None,
            status=str(data.get("status") or "RUNNING"),
            total=int(data.get("total") or 0),
            done=int(data.get("done") or 0),
            passed=int(data.get("passed") or 0),
            failed_facts=int(data.get("failed_facts") or 0),
            failed_abstain=int(data.get("failed_abstain") or 0),
            verdict_reasons=list(data.get("verdict_reasons") or []),
            error=str(data.get("error") or ""),
            started_by=str(data.get("started_by") or ""),
            started_at=str(data.get("started_at") or ""),
            finished_at=str(data.get("finished_at") or ""),
            answer_profile_id=str(data.get("answer_profile_id") or ""),
            judge_profile_id=str(data.get("judge_profile_id") or ""),
            version_ids=list(data.get("version_ids") or []),
            docs_fingerprint=str(data.get("docs_fingerprint") or ""),
            suite_fingerprint=str(data.get("suite_fingerprint") or ""),
        )


@dataclass
class TestRunResultDto(_DictCompatibleDto):
    """Kết quả chấm một câu trong lượt chạy bộ test Knowledge Base."""

    case_id: str
    question: str
    kind: str
    expected_answer: str = ""
    expected_facts: List[str] = field(default_factory=list)
    expected_source: str = ""
    answer: str = ""
    sources: List[str] = field(default_factory=list)
    passed: bool = False
    reasons: List[str] = field(default_factory=list)
    reviewed: bool = False
    approved: bool = False
    review_note: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TestRunResultDto":
        if isinstance(data, cls):
            return data
        return cls(
            case_id=str(data["case_id"]),
            question=str(data["question"]),
            kind=str(data["kind"]),
            expected_answer=str(data.get("expected_answer") or ""),
            expected_facts=list(data.get("expected_facts") or []),
            expected_source=str(data.get("expected_source") or ""),
            answer=str(data.get("answer") or ""),
            sources=list(data.get("sources") or []),
            passed=bool(data.get("passed", False)),
            reasons=list(data.get("reasons") or []),
            reviewed=bool(data.get("reviewed", False)),
            approved=bool(data.get("approved", False)),
            review_note=str(data.get("review_note") or ""),
            reviewed_by=str(data.get("reviewed_by") or ""),
            reviewed_at=str(data.get("reviewed_at") or ""),
        )


@dataclass
class ScopeReadinessDto(_DictCompatibleDto):
    """Trạng thái sẵn sàng xuất bản của một phạm vi kho tri thức."""

    ready: bool
    reasons: List[str] = field(default_factory=list)
    latest_run: Optional[Dict[str, Any]] = None
    draft_count: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ScopeReadinessDto":
        if isinstance(data, cls):
            return data
        latest = data.get("latest_run")
        if isinstance(latest, TestRunSummaryDto):
            latest = latest.to_dict()
        return cls(
            ready=bool(data["ready"]),
            reasons=list(data.get("reasons") or []),
            latest_run=dict(latest) if isinstance(latest, Mapping) else None,
            draft_count=int(data.get("draft_count") or 0),
        )
