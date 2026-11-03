"""Công cụ thử trong AI Console (IPLMS ADR-0050): quyền, không lộ secret, lượt thử tách khỏi số sản phẩm."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.console.dtos import ConsoleActor
from app.core.console.services.tools_service import CONSOLE_TRY_TASK, ToolsService
from app.core.enums import IngestStatus
from app.core.exceptions import ConsoleAccessDenied

ML = ConsoleActor("m-ml", frozenset({"ai_ml_engineer"}))
ANALYST = ConsoleActor("m-an", frozenset({"ai_analyst"}))
DOC = "3f1c2a64-5b7d-4e8f-9a01-23456789abcd"


def service():
    copilot = AsyncMock()
    ingestion = AsyncMock()
    ingestion.ingest.return_value = SimpleNamespace(
        document_id=DOC, status=IngestStatus.SUCCESS, chunk_count=3, process_time=0.25,
        message="ok", version_id="v-1", version_no=2,
    )
    store = AsyncMock()
    return ToolsService(store=store, copilot=copilot, ingestion=ingestion), copilot, ingestion, store


class ConsoleToolsTest(unittest.IsolatedAsyncioTestCase):
    async def test_kiem_cau_hinh_khong_tra_gia_tri_secret(self):
        svc, *_ = service()
        secrets = {
            "AI_LLM_API_KEY": "sk-should-not-leak", "AI_CONSOLE_GOOGLE_CLIENT_SECRET": "gsecret-should-not-leak",
            "AI_DATABASE_URL": "postgresql://u:pw-should-not-leak@h/db",
        }
        from app.config import get_config

        get_config.cache_clear()
        try:
            with patch.dict(os.environ, secrets):
                report = await svc.system_check(ANALYST)
                self.assertTrue(next(c for c in report["checks"] if c["key"] == "llm_key")["ok"])
        finally:
            get_config.cache_clear()  # không để config có secret giả lọt sang test khác
        flat = repr(report)
        self.assertNotIn("should-not-leak", flat)
        self.assertTrue(all(isinstance(c["ok"], bool) for c in report["checks"]))

    async def test_hoi_thu_can_prompt_edit_va_ghi_task_rieng(self):
        svc, copilot, *_ = service()
        with self.assertRaises(ConsoleAccessDenied):
            await svc.try_copilot(ANALYST, "phí gửi xe?")
        await svc.try_copilot(ML, "  phí gửi xe?  ", " lot-1 ")
        request = copilot.ask_question.await_args.args[0]
        self.assertEqual(("phí gửi xe?", "console", "m-ml", "lot-1"),
                         (request.query, request.user_role, request.user_id, request.parking_lot_id))
        self.assertEqual(CONSOLE_TRY_TASK, copilot.ask_question.await_args.kwargs["task"])
        with self.assertRaises(ValueError):
            await svc.try_copilot(ML, "x" * 2001)

    async def test_nap_ban_nhap_kiem_dau_vao_va_ghi_audit(self):
        svc, _, ingestion, store = service()
        with self.assertRaisesRegex(ValueError, "UUID"):
            await svc.ingest_draft(ML, "abc", "quy-che.pdf", b"%PDF")
        with self.assertRaisesRegex(ValueError, "PDF, DOCX"):
            await svc.ingest_draft(ML, DOC, "anh.exe", b"MZ")
        with self.assertRaisesRegex(ValueError, "rỗng"):
            await svc.ingest_draft(ML, DOC, "quy-che.md", b"")
        result = await svc.ingest_draft(ML, DOC, "quy-che.md", b"# Quy che", parking_lot_id="")
        self.assertEqual((True, 3, 2), (result["ok"], result["chunk_count"], result["version_no"]))
        command = ingestion.ingest.await_args.args[0]
        self.assertEqual(("m-ml", None), (command.uploaded_by, command.parking_lot_id))
        self.assertEqual("knowledge.ingest_draft:SUCCESS", store.add_audit.await_args.args[1])


class StudioRealApiTest(unittest.IsolatedAsyncioTestCase):
    """bug-018: các studio gọi service thật trong process console, không hằng số."""

    async def test_anpr_thu_goi_engine_that_khong_luu_anh(self):
        svc, *_ = service()
        fake = SimpleNamespace(plate_number="51A12345", confidence=0.71, vehicle_type=None,
                               plate_color="white", process_time=0.123)
        with patch("app.core.vision.services.anpr_service.AnprService.recognize_bytes", return_value=fake) as run:
            out = await svc.try_anpr(ML, b"jpeg-bytes")
        self.assertFalse(run.call_args.args[1])  # persist_files=False
        self.assertEqual({"plate_number": "51A12345", "confidence": 0.71, "vehicle_type": None,
                          "plate_color": "white", "latency_ms": 123.0, "crop_image": None}, out)

    async def test_anpr_thu_tra_crop_image_base64_khi_co_crop_bytes(self):
        svc, *_ = service()
        fake = SimpleNamespace(plate_number="51A12345", confidence=0.88, vehicle_type="car_sedan",
                               plate_color="white", process_time=0.05, crop_bytes=b"dummy-crop-jpeg")
        with patch("app.core.vision.services.anpr_service.AnprService.recognize_bytes", return_value=fake):
            out = await svc.try_anpr(ML, b"jpeg-bytes")
        self.assertTrue(out["crop_image"].startswith("data:image/jpeg;base64,"))

    async def test_anpr_thu_can_quyen_va_anh_hop_le(self):
        svc, *_ = service()
        with self.assertRaises(ConsoleAccessDenied):
            await svc.try_anpr(ANALYST, b"x")
        with self.assertRaises(ValueError):
            await svc.try_anpr(ML, b"")

    async def test_doi_chieu_xe_khong_tra_diem_chua_do(self):
        svc, *_ = service()
        same = await svc.verify_match(ML, "car_sedan", "car_sedan")
        self.assertEqual({"is_matched": True, "similarity_score": None, "mismatch_reason": "OK"}, same)
        diff = await svc.verify_match(ML, "car_sedan", "motorbike")
        self.assertFalse(diff["is_matched"])
        self.assertEqual("VEHICLE_TYPE_MISMATCH", diff["mismatch_reason"])
        self.assertIsNone(diff["similarity_score"])

    async def test_danh_sach_tai_lieu_tri_thuc_that(self):
        svc, _, ingestion, _ = service()
        ingestion.list.return_value = [SimpleNamespace(
            document_id=DOC, file_name="bang-gia.pdf", category="tariff", chunk_count=4,
            latest_version_no=2, latest_status="DRAFT", published_version_no=1, updated_at="2026-10-24T00:00:00",
        )]
        docs = await svc.knowledge_documents(ML, " lot-1 ")
        ingestion.list.assert_awaited_once_with("lot-1")
        self.assertEqual("bang-gia.pdf", docs[0]["title"])
        self.assertEqual(4, docs[0]["chunk_count"])
        with self.assertRaises(ConsoleAccessDenied):
            await svc.knowledge_documents(ANALYST)
    async def test_xoa_tai_lieu_tri_thuc_can_quyen_va_ghi_audit(self):
        svc, _, ingestion, store = service()
        ingestion.delete.return_value = 1
        with self.assertRaises(ConsoleAccessDenied):
            await svc.delete_knowledge_document(ANALYST, DOC)
        res = await svc.delete_knowledge_document(ML, DOC, " lot-1 ")
        ingestion.delete.assert_awaited_once_with(DOC, "lot-1")
        self.assertEqual(1, res)
        self.assertEqual("knowledge.delete", store.add_audit.await_args.args[1])


    async def test_trang_thai_engine_khong_bia_khi_thieu_weights(self):
        svc, *_ = service()
        with patch.dict(os.environ, {"AI_YOLO_MODEL_PATH": "/khong/ton/tai.pt"}):
            from app.config import get_config

            get_config.cache_clear()
            try:
                engines = (await svc.system_check(ML))["engines"]
            finally:
                get_config.cache_clear()
        self.assertEqual("/khong/ton/tai.pt", engines["yolo_weights_path"])
        self.assertIsNone(engines["yolo_weights_bytes"])
        self.assertIn(engines["yolo_loaded"], (None, False))


class ChatStudioContractTest(unittest.IsolatedAsyncioTestCase):
    """ai bug-017: body Chat Studio gửi phải qua được AskIn và tham số phải tới pipeline."""

    # Giữ khớp ui/src/pages/Copilot/components/ChatStudio/askContract.ts (ASK_BODY_FIELDS).
    UI_FIELDS = ("query", "parking_lot_id", "min_similarity", "top_k", "temperature", "history")
    BODY = {"query": "phí gửi xe?", "parking_lot_id": "", "min_similarity": 0.72, "top_k": 4, "temperature": 0.1, "history": None}

    def test_askin_nhan_dung_body_cua_chat_studio(self):
        from app.api.rest.routes.console_tools_controller import ASK_BODY_FIELDS, AskIn

        self.assertEqual(set(self.UI_FIELDS), set(ASK_BODY_FIELDS))
        self.assertEqual(set(ASK_BODY_FIELDS), set(AskIn.model_fields))
        payload = AskIn.model_validate(self.BODY)
        self.assertEqual({"top_k": 4, "min_similarity": 0.72, "temperature": 0.1, "history": None}, payload.tuning())
        # Thân cũ hai trường vẫn hợp lệ, tham số thử để None = cấu hình mặc định.
        self.assertEqual({"top_k": None, "min_similarity": None, "temperature": None, "history": None},
                         AskIn.model_validate({"query": "x"}).tuning())

    def test_askin_chan_gia_tri_ngoai_bien_va_truong_la(self):
        from pydantic import ValidationError

        from app.api.rest.routes.console_tools_controller import AskIn

        for bad in ({"top_k": 0}, {"top_k": 11}, {"temperature": 1.5}, {"temperature": -0.1},
                    {"min_similarity": 1.2}, {"max_tokens": 512}):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                AskIn.model_validate({**self.BODY, **bad})

    async def test_tham_so_thu_toi_copilot(self):
        svc, copilot, *_ = service()
        await svc.try_copilot(ML, "phí gửi xe?", None, top_k=4, min_similarity=0.72, temperature=0.1)
        request = copilot.ask_question.await_args.args[0]
        self.assertEqual((4, 0.72, 0.1), (request.top_k, request.min_similarity, request.temperature))

    def test_http_stream_khong_con_422(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.rest import console_access
        from app.api.rest.routes import console_tools_controller as ctl

        seen = {}

        async def fake_stream(actor, query, parking_lot_id, **tuning):
            seen.update(tuning)
            yield SimpleNamespace(token="ok", is_finished=True, sources=[], confidence=None, refused=False,
                                  guardrail_triggered=None, prompt_version="v2", turn_id="t", latency_ms=1.0,
                                  speed_tok_s=None, input_tokens=None, output_tokens=None,
                                  context_tokens=None, context_limit=None)

        app = FastAPI()
        app.include_router(ctl.router)
        with patch.object(ctl.tools_service, "try_copilot_stream", fake_stream), \
                patch.object(console_access.auth_service, "authorize_any", AsyncMock(return_value=ML)):
            response = TestClient(app).post("/tools/copilot/stream", json=self.BODY)
        self.assertEqual(200, response.status_code, response.text)
        self.assertIn('"token": "ok"', response.text)
        self.assertEqual({"top_k": 4, "min_similarity": 0.72, "temperature": 0.1, "history": None}, seen)


class RagLimitsTest(unittest.TestCase):
    """Tham số thử chỉ làm truy xuất chặt hơn, không nới cổng NO_CONTEXT (ADR-0029)."""

    def test_min_similarity_khong_ha_duoi_cau_hinh(self):
        from app.core.copilot.engines.rag_pipeline import RagPipelineEngine

        engine = RagPipelineEngine(embedder=object(), vector_store=object(), llm=object())
        engine.top_k, engine.min_similarity = 5, 0.35
        self.assertEqual((5, 0.35), engine._limits(None, None))
        self.assertEqual((4, 0.72), engine._limits(4, 0.72))
        self.assertEqual((2, 0.35), engine._limits(2, 0.0))


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class ConsoleTryNotCountedTest(unittest.TestCase):
    def test_luot_thu_trong_console_khong_vao_so_muc_dung_san_pham(self):
        import psycopg2
        from psycopg2 import sql

        from app.infra.database.ai_request_log_store import AiRequestLogStore

        base = os.environ["AI_TEST_DATABASE_URL"]
        schema = "tools_" + uuid4().hex
        conn = psycopg2.connect(base)
        with conn, conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            sep = "&" if "?" in base else "?"
            store = AiRequestLogStore(f"{base}{sep}options=-csearch_path%3D{schema}", retention_days=30)
            for task in ("copilot_ask", "copilot_stream", CONSOLE_TRY_TASK, CONSOLE_TRY_TASK):
                asyncio.run(store.record({
                    "turn_id": str(uuid4()), "task": task, "status": "SUCCESS", "model": "m",
                    "model_revision": "", "prompt_version": "p", "tools": [], "input_tokens": 1,
                    "output_tokens": 1, "latency_ms": 10, "cost_usd": None, "user_hash": None,
                    "user_role": "member", "parking_lot_id": None, "query_redacted": "q",
                    "answer_redacted": "a", "error_code": None,
                }))
            self.assertEqual(2, asyncio.run(store.summary(7))["total_requests"])
            # Copilot Lab vẫn thấy cả lượt thử để chấm.
            self.assertEqual(4, len(asyncio.run(store.list_recent(10))))
        finally:
            with conn, conn.cursor() as cur:
                cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
            conn.close()



LEAD = ConsoleActor("m-lead", frozenset({"ai_lead"}))
ADMIN = ConsoleActor("m-admin", frozenset({"ai_console_admin"}))
ANNOTATOR = ConsoleActor("m-ann", frozenset({"ai_annotator"}))


class ConsoleSettingsAndToolsEndpointTest(unittest.IsolatedAsyncioTestCase):
    """A-25: Kiểm thử tự động cho các endpoint Settings, Policy, Sessions và gRPC (AUDIT-006)."""

    def setUp(self):
        # A-44: không ghi var/runtime_settings.json thật, không sửa get_config() dùng chung.
        import copy
        import tempfile

        from app.config import get_config

        self._tmp = tempfile.TemporaryDirectory()
        self._settings_path = os.path.join(self._tmp.name, "runtime_settings.json")
        cfg = copy.deepcopy(get_config())
        self._patches = [
            patch("app.config.runtime_override_config.RUNTIME_SETTINGS_PATH", self._settings_path),
            patch("app.core.console.services.tools_service.get_config", return_value=cfg),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    async def test_settings_policy_requires_threshold_permission(self):
        svc, _, _, store = service()
        # ML Engineer chỉ có ai:prompt:edit, không có ai:policy:threshold -> Bị từ chối (BUG-06)
        with self.assertRaises(ConsoleAccessDenied):
            await svc.update_policy_settings(ML, {"rag_min_similarity": 0.6})

        # Lead có quyền ai:policy:threshold -> Cập nhật thành công, lý do vào audit
        res = await svc.update_policy_settings(LEAD, {"rag_min_similarity": 0.6, "rag_top_k": 7, "reason": "đo held-out"})
        self.assertIn("policy", res)
        self.assertEqual("settings.policy", store.add_audit.await_args.args[1])
        self.assertIn("đo held-out", store.add_audit.await_args.args[4])
        self.assertTrue(os.path.isfile(self._settings_path))

    async def test_compute_khong_doi_provider_hay_model(self):
        import json

        from app.core.console.services import tools_service

        svc, *_ = service()
        cfg = tools_service.get_config()
        before = (cfg.llm.llm_provider, cfg.llm.llm_model)
        # REQ-020 X2 / ADR-0061 §2: model theo tác vụ đổi bằng revision, Settings không nhận nữa.
        for payload in ({"llm_provider": "openai"}, {"llm_provider": "ollama"}, {"llm_model": "qwen3:4b"}):
            with self.assertRaises(ValueError):
                await svc.update_compute_settings(ML, payload)
        # Preset chỉ đổi phần cứng, không lặng lẽ chuyển provider.
        await svc.update_compute_settings(ML, {"preset": "cpu_eco"})
        self.assertEqual(before, (cfg.llm.llm_provider, cfg.llm.llm_model))
        with open(self._settings_path, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertNotIn("llm_provider", saved)
        self.assertNotIn("llm_model", saved)

    async def test_settings_hien_model_inference_dung_that(self):
        from app.infra.database.model_policy_store import model_policy_store

        svc, *_ = service()
        active = {"id": "p-1", "task": "copilot_answer", "revision": 4, "provider": "openai",
                  "model": "gpt-profile", "timeout_seconds": 30, "max_output_tokens": 800,
                  "reasoning_effort": "none"}

        async def get_active(task):
            return active if task == "copilot_answer" else None

        with patch.object(model_policy_store, "db_url", "postgresql://test"),                 patch.object(model_policy_store, "get_active", side_effect=get_active):
            res = await svc.get_runtime_settings(ML)
            check = await svc.system_check(ML)
        models = {m["task"]: m for m in res["models"]}
        self.assertEqual(("profile", "gpt-profile", 4), (
            models["copilot_answer"]["source"], models["copilot_answer"]["model"], models["copilot_answer"]["revision"]))
        self.assertEqual("env", models["test_judge"]["source"])
        self.assertEqual("gpt-profile", check["llm_model"])
        self.assertNotIn("llm_model", res["compute"])

    async def test_settings_kho_profile_loi_thi_bao_unknown(self):
        from app.infra.database.model_policy_store import model_policy_store

        svc, *_ = service()
        with patch.object(model_policy_store, "db_url", "postgresql://test"),                 patch.object(model_policy_store, "get_active", side_effect=RuntimeError("db down")):
            res = await svc.get_runtime_settings(ML)
        # Không đoán là env khi không biết revision nào đang dùng.
        self.assertEqual({"unknown"}, {m["source"] for m in res["models"]})

    def test_file_override_cu_con_llm_model_bi_bo_qua(self):
        import json

        from app.config.runtime_override_config import apply_runtime_overrides

        cfg = SimpleNamespace(llm=SimpleNamespace(llm_model="env-model", llm_provider="ollama", rag_top_k=5),
                              vision=SimpleNamespace(), telemetry=SimpleNamespace(), console=SimpleNamespace())
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump({"llm_model": "file-model", "llm_provider": "local", "rag_top_k": 7}, f)
        apply_runtime_overrides(cfg)
        self.assertEqual(("env-model", "ollama", 7), (cfg.llm.llm_model, cfg.llm.llm_provider, cfg.llm.rag_top_k))

    async def test_ghi_file_loi_thi_hoan_tac_cau_hinh(self):
        from app.core.console.services import tools_service

        from app.config.runtime_override_config import snapshot_runtime_fields

        svc, *_ = service()
        cfg = tools_service.get_config()
        cfg.llm.llm_provider = "ollama"
        before = snapshot_runtime_fields(cfg)
        # Lỗi ở chính os.replace (vd Windows khoá file đích) chứ không chỉ ở hàm ghi bị giả lập.
        with patch("app.config.runtime_override_config.os.replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                await svc.update_policy_settings(LEAD, {"rag_top_k": 19, "reason": "thử lỗi ghi"})
            with self.assertRaises(PermissionError):
                await svc.update_compute_settings(ML, {"local_llm_threads": 63})
            with self.assertRaises(PermissionError):
                await svc.update_compute_settings(ML, {"preset": "cpu_eco"})
        # A-53: API báo lỗi thì cấu hình đang chạy giữ nguyên, kể cả provider; không để lại tệp tạm.
        self.assertEqual(before, snapshot_runtime_fields(cfg))
        self.assertFalse(os.path.exists(self._settings_path + ".tmp"))

    def test_file_override_hong_khong_ap_do_dang(self):
        import json

        from app.config.runtime_override_config import apply_runtime_overrides

        cfg = SimpleNamespace(llm=SimpleNamespace(rag_top_k=5, rag_min_similarity=0.35), vision=SimpleNamespace(),
                              telemetry=SimpleNamespace(), console=SimpleNamespace())
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump({"rag_top_k": 9, "rag_min_similarity": "không-phải-số"}, f)
        apply_runtime_overrides(cfg)
        self.assertEqual(5, cfg.llm.rag_top_k)
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump({"rag_top_k": 99, "llm_provider": "openai"}, f)
        apply_runtime_overrides(cfg)
        self.assertEqual(20, cfg.llm.rag_top_k)
        self.assertFalse(hasattr(cfg.llm, "llm_provider"))

    async def test_list_sessions_delegates_and_marks_current(self):
        # bug-030: kiểm tra list_sessions uỷ quyền store và đánh dấu is_current
        svc, _, _, store = service()
        store.list_active_sessions.return_value = [
            {"session_id": "sess-active-01", "member_id": "m-admin", "mfa_verified": True},
            {"session_id": "sess-other-02", "member_id": "m-admin", "mfa_verified": True},
        ]
        current_actor = ConsoleActor("m-admin", frozenset({"ai_console_admin"}), session_id="sess-active-01")
        sessions = await svc.list_sessions(current_actor)
        store.list_active_sessions.assert_awaited_once_with("m-admin", include_all=True)
        self.assertEqual(2, len(sessions))
        self.assertTrue(sessions[0]["is_current"])
        self.assertFalse(sessions[1]["is_current"])

    async def test_revoke_active_session_guards(self):
        svc, _, _, store = service()
        store.revoke_target_session.return_value = True
        current_actor = ConsoleActor("m-admin", frozenset({"ai_console_admin"}), session_id="sess-active-01")

        # Cấm tự thu hồi phiên hiện tại đang dùng (BUG-09)
        with self.assertRaisesRegex(ValueError, "Không thể tự thu hồi phiên đang hoạt động"):
            await svc.revoke_session_by_id(current_actor, "sess-active-01")

        # Thu hồi phiên khác của người dùng -> Thành công
        res = await svc.revoke_session_by_id(current_actor, "sess-other-02", "Dọn dẹp phiên cũ")
        self.assertTrue(res["revoked"])

    async def test_engine_reload_llm_action(self):
        svc, _, _, store = service()
        with patch("app.core.console.services.tools_service._reload_llm", return_value={"status": "reloaded", "model": "test-model"}) as mock_reload:
            res = await svc.engine_action(ML, "reload_llm")
            self.assertIn("compute", res)
            self.assertIn("engines", res)
            self.assertEqual("engine.reload_llm", store.add_audit.await_args.args[1])
            mock_reload.assert_called_once()

    async def test_annotator_cannot_access_settings(self):
        svc, *_ = service()
        with self.assertRaises(ConsoleAccessDenied):
            await svc.get_runtime_settings(ANNOTATOR)

    async def test_forecast_simulation_schema_alignment(self):
        svc, *_ = service()
        res = await svc.simulate_forecast(ANALYST, area_id="lot_landmark_81", day_of_week=3, total_capacity=300)
        quote = res["stage3_inference"]["surge_quote"]
        # Phải có đầy đủ reason_code và occupancy_pct theo đúng hợp đồng UI (BUG-12)
        self.assertIn("reason_code", quote)
        self.assertIn("occupancy_pct", quote)
        self.assertIn("current_occupancy_pct", quote)
        # A-11/12: hợp đồng giờ khớp kiểu UI, không gắn tên model chưa có.
        inference = res["stage3_inference"]
        self.assertEqual(24, len(inference["hourly_predictions"]))
        self.assertEqual(
            {"hour_of_day", "predicted_occupancy_pct", "estimated_free_spots", "surge_multiplier", "confidence"},
            set(inference["hourly_predictions"][0]),
        )
        expected = "heuristic-baseline" if inference["is_fallback"] else "profile-7x24"
        self.assertEqual(expected, inference["model_version"])
        # Bãi không có trong lake → baseline, và số bản ghi là số thật của dataset (không phải hằng).
        self.assertTrue(inference["is_fallback"])
        self.assertGreater(res["stage1_datalake"]["total_records"], 0)
        self.assertEqual(len(res["stage2_features"]["sample_rows"]) > 0, res["stage2_features"]["total_samples"] > 0)

    async def test_grpc_dataset_handler_exports_without_name_error(self):
        from unittest.mock import MagicMock
        from app.api.grpc.handlers.dataset_handler import DatasetHandler

        handler = DatasetHandler()
        ctx = MagicMock()
        req_policy = MagicMock()
        req_policy.model_name = "anpr"

        with patch("app.core.console.services.accept_policy_service.accept_policy_service.approved", new_callable=AsyncMock) as mock_approved:
            mock_approved.return_value = {
                "id": "pol-1",
                "model_name": "anpr",
                "version": 1,
                "auto_accept_threshold": 0.85,
                "audit_rate": 0.05,
                "decided_at": "2026-10-25T00:00:00Z",
            }
            res = await handler.GetAcceptPolicy(req_policy, ctx)
            self.assertIsNotNone(res)


if __name__ == "__main__":
    unittest.main()
