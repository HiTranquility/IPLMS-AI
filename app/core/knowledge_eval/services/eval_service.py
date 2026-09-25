"""Điều phối bộ test Knowledge Base: test case, lượt chạy nền, cổng xuất bản (ISSUE-009).

Scope = `parking_lot_id` (ID ParkingArea) hoặc None = tài liệu chung. Quyền
theo scope do backend kiểm TRƯỚC khi gọi vào đây.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set

from app.config import get_config
from app.core.copilot.engines.rag_pipeline import rag_pipeline
from app.core.exceptions import KnowledgeGateError, ModelNotLoadedError, RagPipelineError
from app.core.knowledge_eval.engines import case_generator, gate, judge
from app.core.knowledge_eval.engines.grader import KINDS, grade
from app.infra.database.knowledge_eval_store import knowledge_eval_store
from app.infra.database.pgvector_client import pgvector_client
from app.infra.llm.llm_factory import llm_factory
from app.util.logger import logger

_MAX_QUESTION = 500
_MAX_ANSWER = 2000


class KnowledgeEvalService:
    def __init__(self, store=None, vector_store=None, rag=None, llm=None) -> None:
        self.store = store or knowledge_eval_store
        self.vector_store = vector_store or pgvector_client
        self.rag = rag or rag_pipeline
        self.llm = llm or llm_factory
        self.config = get_config().eval
        # Giữ tham chiếu tới task nền: asyncio chỉ giữ weak-ref, thiếu dòng này
        # task có thể bị thu gom giữa chừng.
        self._tasks: Set[asyncio.Task] = set()

    # ── test cases ───────────────────────────────────────────────────────────
    async def list_cases(self, scope: Optional[str]) -> List[Dict[str, Any]]:
        return await self.store.list_cases(scope)

    async def upsert_case(self, case: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
        question = (case.get("question") or "").strip()
        if not question:
            raise ValueError("Câu hỏi không được để trống.")
        if len(question) > _MAX_QUESTION or len(case.get("expected_answer") or "") > _MAX_ANSWER:
            raise ValueError("Câu hỏi tối đa 500 ký tự, đáp án tối đa 2000 ký tự.")
        if case.get("kind") not in KINDS:
            raise ValueError("Loại câu hỏi phải là fact, explain hoặc abstain.")
        facts = [f.strip() for f in case.get("expected_facts") or [] if f and f.strip()]
        if case["kind"] == "fact" and not facts:
            raise ValueError("Câu loại fact cần ít nhất một thông tin bắt buộc (vd 25.000đ).")
        return await self.store.upsert_case(
            {
                **case,
                "question": question,
                "expected_facts": [] if case["kind"] == "abstain" else facts,
                "expected_source": "" if case["kind"] == "abstain" else (case.get("expected_source") or "").strip(),
            },
            actor_id,
        )

    async def delete_case(self, case_id: str, scope: Optional[str]) -> bool:
        return await self.store.delete_case(case_id, scope)

    async def generate_cases(self, scope: Optional[str], max_cases: int) -> List[Dict[str, Any]]:
        limit = max(1, min(max_cases or self.config.max_generated_cases, self.config.max_generated_cases))
        version_ids = await self.vector_store.latest_version_ids(scope)
        if not version_ids:
            raise KnowledgeGateError("Chưa có tài liệu nào trong phạm vi này để AI đọc và soạn câu hỏi.")
        chunks = await self.store.chunks_for_versions(version_ids, limit=40)
        payload = await self.llm.generate_json(
            case_generator.GENERATOR_INSTRUCTIONS,
            case_generator.build_generator_input(chunks, limit),
            "knowledge_test_cases",
            case_generator.GENERATOR_SCHEMA,
        )
        proposals = case_generator.clean_proposals(payload, {c["source"] for c in chunks}, limit)
        return [{**p, "id": "", "parking_lot_id": scope} for p in proposals]

    # ── runs ─────────────────────────────────────────────────────────────────
    async def start_run(self, scope: Optional[str], started_by: str) -> Dict[str, Any]:
        cases = await self.store.list_cases(scope)
        if not cases:
            raise KnowledgeGateError("Bộ test đang trống — thêm câu hỏi trước khi chạy.")
        if len(cases) > self.config.max_cases_per_run:
            raise KnowledgeGateError(
                f"Bộ test có {len(cases)} câu, vượt trần {self.config.max_cases_per_run} câu mỗi lượt."
            )
        version_ids = await self.vector_store.latest_version_ids(scope)
        if not version_ids:
            raise KnowledgeGateError("Chưa có tài liệu nào trong phạm vi này để test.")
        run = await self.store.create_run(
            scope,
            started_by,
            total=len(cases),
            version_ids=version_ids,
            docs_fingerprint=gate.fingerprint(version_ids),
            suite_fingerprint=gate.suite_fingerprint(cases),
            max_concurrent=self.config.max_concurrent_runs,
        )
        task = asyncio.create_task(self._execute(run["id"], scope, cases, version_ids))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run

    async def _execute(
        self, run_id: str, scope: Optional[str], cases: List[Dict[str, Any]], version_ids: List[str]
    ) -> None:
        passed = failed_facts = failed_abstain = 0
        try:
            for ordinal, case in enumerate(cases):
                result = await self._run_case(case, scope)
                passed += int(result["passed"])
                if not result["passed"]:
                    failed_facts += int(case["kind"] == "fact")
                    failed_abstain += int(case["kind"] == "abstain")
                await self.store.add_result(run_id, ordinal, result)
        except (ModelNotLoadedError, RagPipelineError) as exc:
            # Hạ tầng hỏng (chưa có key, DB/LLM lỗi): cả lượt không có giá trị,
            # KHÔNG được tính là "trượt" do tài liệu.
            logger.warning("Knowledge test run %s failed: %s", run_id, exc)
            await self._safe_finish(run_id, "FAILED", error=str(exc))
            return
        except Exception as exc:  # pragma: no cover - lỗi lập trình
            logger.exception("Knowledge test run %s crashed", run_id)
            await self._safe_finish(run_id, "FAILED", error=f"Lượt chạy lỗi ngoài dự kiến: {exc}")
            return

        ok, reasons = gate.run_verdict(
            len(cases),
            passed,
            failed_facts,
            failed_abstain,
            self.config.min_cases,
            self.config.min_pass_ratio,
        )
        await self._safe_finish(
            run_id,
            "PASSED" if ok else "FAILED",
            failed_facts=failed_facts,
            failed_abstain=failed_abstain,
            verdict_reasons=reasons,
        )
        # Chỉ gắn nhãn TESTED khi tài liệu vẫn đúng như lúc chạy (không ai nạp
        # thêm giữa chừng) — nếu không, nhãn sẽ nói dối về bản chưa được test.
        if gate.fingerprint(await self.vector_store.latest_version_ids(scope)) == gate.fingerprint(version_ids):
            await self.vector_store.mark_versions_tested(version_ids, ok)

    async def _run_case(self, case: Dict[str, Any], scope: Optional[str]) -> Dict[str, Any]:
        answer = await self.rag.query(case["question"], parking_lot_id=scope, preview=True)
        sources = list(answer.get("sources") or [])
        result = grade(
            case["kind"],
            answer["answer"],
            sources,
            case.get("expected_facts") or [],
            case.get("expected_source") or "",
            retrieved_nothing=not sources,
        )
        reasons = list(result.reasons)
        passed = result.passed
        if result.needs_judge and self.config.judge_enabled and case.get("expected_answer"):
            payload = await self.llm.generate_json(
                judge.JUDGE_INSTRUCTIONS,
                judge.build_judge_input(case["question"], case["expected_answer"], answer["answer"]),
                "knowledge_judge_verdict",
                judge.JUDGE_SCHEMA,
                model=self.config.judge_model or None,
            )
            passed, reason = judge.parse_verdict(payload)
            reasons.append(f"Giám khảo AI: {reason}")
        return {
            "case_id": case["id"],
            "question": case["question"],
            "kind": case["kind"],
            "expected_answer": case.get("expected_answer") or "",
            "expected_facts": case.get("expected_facts") or [],
            "answer": answer["answer"],
            "sources": sources,
            "passed": passed,
            "reasons": reasons,
        }

    async def _safe_finish(self, run_id: str, status: str, **kwargs) -> None:
        try:
            await self.store.finish_run(run_id, status, **kwargs)
        except Exception:  # pragma: no cover - DB chết giữa chừng: nhịp tim sẽ tự báo ABORTED
            logger.exception("Could not finish knowledge test run %s", run_id)

    async def get_run(self, run_id: str, scope: Optional[str]) -> Dict[str, Any]:
        run = await self.store.get_run(run_id, scope)
        if run is None:
            raise KnowledgeGateError("Không tìm thấy lượt chạy trong phạm vi này.")
        return {"run": run, "results": await self.store.list_results(run_id)}

    async def list_runs(self, scope: Optional[str]) -> List[Dict[str, Any]]:
        return await self.store.list_runs(scope)

    # ── cổng xuất bản ────────────────────────────────────────────────────────
    async def readiness(self, scope: Optional[str]) -> Dict[str, Any]:
        runs = await self.store.list_runs(scope, limit=1)
        latest = runs[0] if runs else None
        docs_fp = gate.fingerprint(await self.vector_store.latest_version_ids(scope))
        suite_fp = gate.suite_fingerprint(await self.store.list_cases(scope))
        unpublished = await self.store.count_unpublished(latest["version_ids"]) if latest else 0
        reasons = gate.readiness(latest, docs_fp, suite_fp, unpublished)
        return {
            "ready": not reasons,
            "reasons": reasons,
            "latest_run": latest,
            "draft_count": unpublished,
        }

    async def publish(self, scope: Optional[str], published_by: str) -> int:
        state = await self.readiness(scope)
        if not state["ready"]:
            raise KnowledgeGateError("Chưa được xuất bản: " + " ".join(state["reasons"]))
        return await self.vector_store.publish_versions(
            scope, state["latest_run"]["version_ids"], published_by
        )


knowledge_eval_service = KnowledgeEvalService()
