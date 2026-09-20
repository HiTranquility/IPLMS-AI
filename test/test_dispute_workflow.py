import importlib.util
import unittest

from app.core.copilot.engines.dispute_workflow.dependencies import (
    DisputeWorkflowDependencies,
)
from app.core.copilot.engines.dispute_workflow.graph import build_dispute_graph
from app.core.copilot.engines.dispute_workflow.nodes import (
    finalize,
    make_analyze_evidence_node,
    make_draft_recommendation_node,
    make_load_evidence_node,
    make_retrieve_policy_node,
    route_after_review,
    route_after_validation,
    validate_evidence,
)
from app.core.copilot.engines.dispute_workflow.state import (
    assert_json_safe,
    make_initial_state,
    validate_review,
)
from app.core.exceptions import WorkflowConfigurationError, WorkflowStateError
from app.infra.workflow import open_workflow_checkpointer


LANGGRAPH_INSTALLED = importlib.util.find_spec("langgraph") is not None


class _EvidenceClient:
    def __init__(self, *, complete=True):
        self.complete = complete

    async def load_bundle(self, _bundle_id):
        return {
            "version": "evidence-v3",
            "parking_lot_id": "lot-1",
            "session": {"id": "session-1", "fee": 50000},
            "media_refs": (
                [
                    {"provider": "s3", "key": "check-in.jpg"},
                    {"provider": "s3", "key": "check-out.jpg"},
                ]
                if self.complete
                else []
            ),
        }


class _Analyzer:
    def __init__(self, *, complete=True):
        self.complete = complete

    async def analyze(self, *, media_refs, session_snapshot):
        if not self.complete or not media_refs:
            return []
        return [{"kind": "plate_match", "matched": True, "model_version": "anpr-v1"}]


class _Retriever:
    def __init__(self, *, complete=True):
        self.complete = complete

    async def retrieve(self, *, query, parking_lot_id):
        if not self.complete:
            return []
        return [
            {
                "chunk_id": "chunk-1",
                "source": "quy-che-bai-1.pdf",
                "content": "Phí phải khớp thời gian thực tế.",
                "similarity": 0.91,
            }
        ]


class _Writer:
    def __init__(self):
        self.calls = 0

    async def draft(self, state):
        self.calls += 1
        return {
            "action": "MANUAL_REVIEW",
            "recommended_refund": 0,
            "justification": f"Đối chiếu {len(state['policy_chunks'])} nguồn.",
        }


def _dependencies(*, complete=True):
    writer = _Writer()
    return (
        DisputeWorkflowDependencies(
            evidence_client=_EvidenceClient(complete=complete),
            evidence_analyzer=_Analyzer(complete=complete),
            policy_retriever=_Retriever(complete=complete),
            recommendation_writer=writer,
        ),
        writer,
    )


def _state(workflow_id="workflow-1"):
    return make_initial_state(
        workflow_id=workflow_id,
        dispute_id="dispute-1",
        evidence_bundle_id="bundle-1",
        actor_id="staff-1",
        claim_reason="Tôi bị tính thừa phí.",
        claimed_amount=50000,
    )


class DisputeWorkflowStateTest(unittest.TestCase):
    def test_rejects_negative_claim_and_checkpoint_secrets(self):
        with self.assertRaises(WorkflowStateError):
            make_initial_state(
                workflow_id="workflow-1",
                dispute_id="dispute-1",
                evidence_bundle_id="bundle-1",
                actor_id="staff-1",
                claim_reason="Sai phí",
                claimed_amount=-1,
            )
        with self.assertRaises(WorkflowStateError):
            assert_json_safe({"signed_url": "https://temporary.example"})
        with self.assertRaises(WorkflowStateError):
            assert_json_safe({"image": b"raw bytes"})

    def test_review_requires_known_action_and_reviewer(self):
        self.assertEqual(
            validate_review({"action": "approve", "reviewer_id": "staff-1"})["action"],
            "approve",
        )
        with self.assertRaises(WorkflowStateError):
            validate_review({"action": "refund", "reviewer_id": "staff-1"})
        with self.assertRaises(WorkflowStateError):
            validate_review({"action": "approve", "reviewer_id": ""})


class DisputeWorkflowNodeTest(unittest.IsolatedAsyncioTestCase):
    async def test_complete_evidence_reaches_draft_and_safe_backend_command(self):
        deps, writer = _dependencies()
        state = _state()
        for node in (
            make_load_evidence_node(deps),
            make_analyze_evidence_node(deps),
            make_retrieve_policy_node(deps),
            validate_evidence,
            make_draft_recommendation_node(deps),
        ):
            state.update(await node(state))

        self.assertEqual(route_after_validation(state), "draft")
        self.assertEqual(writer.calls, 1)
        state.update(
            {
                "review": {
                    "action": "approve",
                    "reviewer_id": "staff-2",
                    "comment": "Đã kiểm tra nguồn.",
                },
                "status": "review_approved",
            }
        )
        self.assertEqual(route_after_review(state), "finalize")
        state.update(await finalize(state))
        self.assertEqual(state["status"], "approved_for_backend")
        self.assertEqual(
            state["approved_command"]["operation_key"],
            "workflow-1:approved-action:v1",
        )
        self.assertNotIn("payment", state["approved_command"])

    async def test_missing_evidence_skips_recommendation(self):
        deps, writer = _dependencies(complete=False)
        state = _state()
        for node in (
            make_load_evidence_node(deps),
            make_analyze_evidence_node(deps),
            make_retrieve_policy_node(deps),
            validate_evidence,
        ):
            state.update(await node(state))

        self.assertEqual(route_after_validation(state), "review")
        self.assertEqual(state["status"], "evidence_incomplete")
        self.assertIn("check_in_out_media", state["missing_evidence"])
        self.assertIn("applicable_policy", state["missing_evidence"])
        self.assertEqual(writer.calls, 0)

    async def test_unknown_checkpoint_backend_fails_closed(self):
        with self.assertRaisesRegex(
            WorkflowConfigurationError, "Checkpoint backend không hỗ trợ"
        ):
            async with open_workflow_checkpointer(backend="redis"):
                self.fail("unsupported backend must not yield a checkpointer")

    async def test_postgres_checkpoint_requires_explicit_database_url(self):
        with self.assertRaisesRegex(
            WorkflowConfigurationError,
            "AI_WORKFLOW_CHECKPOINT_DATABASE_URL là bắt buộc",
        ):
            async with open_workflow_checkpointer(
                backend="postgres",
                database_url="",
            ):
                self.fail("postgres backend must not open without a database URL")


@unittest.skipUnless(LANGGRAPH_INSTALLED, "langgraph dependency chưa được cài")
class DisputeGraphIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_graph_interrupts_and_resumes_after_approval(self):
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import Command

        deps, _writer = _dependencies()
        graph = build_dispute_graph(deps, checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "workflow-graph-approve"}}

        paused = await graph.ainvoke(_state("workflow-graph-approve"), config)
        self.assertIn("__interrupt__", paused)
        self.assertEqual(paused["status"], "awaiting_review")

        result = await graph.ainvoke(
            Command(
                resume={
                    "action": "approve",
                    "reviewer_id": "staff-2",
                    "comment": "Đồng ý với đề xuất.",
                }
            ),
            config,
        )
        self.assertEqual(result["status"], "approved_for_backend")
        self.assertEqual(result["review"]["reviewer_id"], "staff-2")

    async def test_graph_rejection_has_no_backend_command(self):
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import Command

        deps, _writer = _dependencies()
        graph = build_dispute_graph(deps, checkpointer=InMemorySaver())
        config = {"configurable": {"thread_id": "workflow-graph-reject"}}

        paused = await graph.ainvoke(_state("workflow-graph-reject"), config)
        self.assertIn("__interrupt__", paused)
        self.assertEqual(paused["status"], "awaiting_review")
        result = await graph.ainvoke(
            Command(resume={"action": "reject", "reviewer_id": "staff-3"}),
            config,
        )
        self.assertEqual(result["status"], "rejected")
        self.assertNotIn("approved_command", result)


if __name__ == "__main__":
    unittest.main()
