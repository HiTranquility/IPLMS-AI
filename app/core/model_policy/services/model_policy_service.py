"""Draft, probe, and activate model profiles by AI task."""
from __future__ import annotations

from app.config import get_config
from app.core.exceptions import KnowledgeGateError
from app.core.model_policy.engines.validation import clean_profile
from app.core.knowledge_eval.engines import gate
from app.core.knowledge_eval.engines import case_generator, judge
from app.infra.database.model_policy_store import model_policy_store
from app.infra.database.knowledge_eval_store import knowledge_eval_store
from app.infra.llm.llm_factory import LlmFactory


class ModelPolicyService:
    def __init__(self, store=None) -> None:
        self.store = store or model_policy_store

    async def list_profiles(self) -> list[dict]:
        return await self.store.list_profiles()

    async def create_profile(self, values: dict, actor: str) -> dict:
        return await self.store.create_profile(clean_profile(values), actor)

    async def test_profile(self, profile_id: str) -> dict:
        profile = await self.store.get_profile(profile_id)
        if not profile:
            raise KnowledgeGateError("Không tìm thấy hồ sơ model.")
        if profile["provider"] == "openai" and not get_config().llm.llm_api_key:
            raise KnowledgeGateError("Chưa cấp AI_LLM_API_KEY cho AI service.")
        if profile["provider"] == "ollama" and not get_config().llm.llm_base_url:
            raise KnowledgeGateError("Chưa cấp AI_LLM_BASE_URL cho Ollama.")
        llm = LlmFactory(profile=profile)
        if profile["task"] == "copilot_answer":
            answer = await llm.generate_response(
                "Trả lời ngắn gọn bằng tiếng Việt. Không dùng thông tin ngoài ngữ cảnh.",
                "Tên bãi xe là gì?", "Tên bãi xe: Bãi thử IPLMS.",
            )
            if "IPLMS" not in answer:
                raise KnowledgeGateError("Model không dùng đúng ngữ cảnh trong câu thử.")
        elif profile["task"] == "test_generation":
            payload = await llm.generate_json(
                case_generator.GENERATOR_INSTRUCTIONS,
                case_generator.build_generator_input(
                    [{"source": "test.txt", "content": "Bãi thử mở cửa lúc 06:00."}], 1
                ),
                "knowledge_test_cases", case_generator.GENERATOR_SCHEMA,
            )
            if not case_generator.clean_proposals(payload, ["test.txt"], 1):
                raise KnowledgeGateError("Model chưa sinh được câu hỏi hợp lệ từ tài liệu thử.")
        else:
            for answer, expected in (("Bãi mở cửa lúc 06:00.", True),
                                     ("Bãi mở cửa lúc 09:00.", False)):
                payload = await llm.generate_json(
                    judge.JUDGE_INSTRUCTIONS,
                    judge.build_judge_input(
                        "Bãi mở cửa lúc mấy giờ?", "Bãi mở cửa lúc 06:00.", answer
                    ),
                    "knowledge_judge_verdict", judge.JUDGE_SCHEMA,
                )
                if judge.parse_verdict(payload)[0] != expected:
                    raise KnowledgeGateError("Model chấm sai câu kiểm tra cố định.")
        return await self.store.mark_tested(profile_id)

    async def activate(self, profile_id: str, actor: str) -> dict:
        profile = await self.store.get_profile(profile_id)
        if not profile:
            raise KnowledgeGateError("Không tìm thấy hồ sơ model.")
        if profile["task"] != "copilot_answer":
            return await self.store.activate(profile_id, actor)
        await knowledge_eval_store.ensure_schema()

        def validate(candidate, run, versions, cases, reviewed, rejected, active_judge_id):
            if not run or run[5] != candidate["id"]:
                return ["Chạy bộ test RAG chung với đúng hồ sơ ứng viên trước."]
            reasons = []
            if run[1] != "PASSED":
                reasons.append("Bộ test RAG ứng viên chưa đạt.")
            if run[3] != gate.fingerprint(versions) or run[4] != gate.suite_fingerprint(cases):
                reasons.append("Tài liệu hoặc bộ test đã thay đổi; chạy lại.")
            if reviewed != run[2] or rejected:
                reasons.append("Cần duyệt OK mọi câu trong lượt chạy ứng viên.")
            if (run[6] or "") != active_judge_id:
                reasons.append("Model chấm bài đã đổi sau lượt test — chạy lại.")
            return reasons

        return await self.store.activate(profile_id, actor, validate)


model_policy_service = ModelPolicyService()
