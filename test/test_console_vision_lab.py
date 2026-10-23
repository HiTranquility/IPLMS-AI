"""AI Console P3–P5 trên Postgres thật: gán → duyệt bốn mắt → snapshot → đo → promote → ngưỡng."""
import asyncio
import hashlib
import os
import unittest
from uuid import uuid4

from app.core.console.dtos import ConsoleActor, ExportedCapture
from app.core.console.engines.audit_accuracy import accuracy_report, wilson_interval
from app.core.exceptions import ConsoleAccessDenied, ConsoleStoreError

IMG = b"\xff\xd8 crop"
SHA = hashlib.sha256(IMG).hexdigest()
WEIGHTS = "c" * 64


class AuditAccuracyTest(unittest.TestCase):
    def test_khop_dem_tay_tren_20_mau(self):
        # 20 mẫu audit: 10 mẫu conf 0.95 (đúng cả 10), 6 mẫu conf 0.80 (đúng 4), 4 mẫu conf 0.60 (đúng 1).
        samples = (
            [{"machine_plate": "51A-123.45", "truth": "51A12345", "confidence": 0.95}] * 10
            + [{"machine_plate": "51A12345", "truth": "51A12345", "confidence": 0.80}] * 4
            + [{"machine_plate": "51A12346", "truth": "51A12345", "confidence": 0.80}] * 2
            + [{"machine_plate": "51A12345", "truth": "51A12345", "confidence": 0.60}] * 1
            + [{"machine_plate": "", "truth": "51A12345", "confidence": 0.60}] * 3
        )
        report = accuracy_report(samples, min_samples=10)
        self.assertEqual((20, 15, 0.75), (report["total"], report["correct"], report["accuracy"]))
        at = {c["threshold"]: c for c in report["curve"]}
        self.assertEqual((16, 0.875), (at[0.80]["total"], at[0.80]["accuracy"]))
        self.assertEqual((10, 1.0), (at[0.81]["total"], at[0.81]["accuracy"]))
        # Ngưỡng thấp nhất đạt ≥ 98% với ≥ 10 mẫu phía trên.
        self.assertEqual(0.81, report["suggested_threshold"])
        self.assertEqual((6, 4), (report["buckets"][8]["total"], report["buckets"][8]["correct"]))

    def test_it_mau_thi_khong_de_xuat_va_noi_ro(self):
        report = accuracy_report([{"machine_plate": "A", "truth": "A", "confidence": 0.99}] * 5)
        self.assertIsNone(report["suggested_threshold"])
        self.assertIn("ít nhất 20", report["suggestion_reason"])

    def test_wilson(self):
        self.assertIsNone(wilson_interval(0, 0))
        low, high = wilson_interval(15, 20)
        self.assertTrue(0.5 < low < 0.75 < high < 0.92)


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class VisionLabFlowTest(unittest.TestCase):
    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        from app.core.console.services.accept_policy_service import ConsoleAcceptPolicyService
        from app.core.console.services.model_lab_service import ConsoleModelLabService
        from app.core.console.services.vision_import_service import ConsoleVisionImportService
        from app.core.console.services.vision_lab_service import ConsoleVisionLabService
        from app.infra.database.console_vision_store import ConsoleVisionStore
        from app.infra.identity.password import hash_password

        base_url = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "vision_lab_" + uuid4().hex
        self.admin_conn = psycopg2.connect(base_url)
        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        sep = "&" if "?" in base_url else "?"
        self.store = ConsoleVisionStore(f"{base_url}{sep}options=-csearch_path%3D{self.schema}")
        self.importer = ConsoleVisionImportService(store=self.store, fetch=lambda url: IMG, retention_days=90)
        self.lab = ConsoleVisionLabService(store=self.store)
        self.models = ConsoleModelLabService(
            store=self.store,
            run=lambda image: {"plate_number": "51A12345", "confidence": 0.9, "process_time": 0.01},
            engine_version=lambda: f"yolo:{WEIGHTS[:12]}+easyocr:1.7",
        )
        self.policies = ConsoleAcceptPolicyService(store=self.store)

        def member(email, *roles):
            member_id = asyncio.run(self.store.create_emergency_admin(
                email, email, hash_password("mật-khẩu-đủ-dài-123"), None, roles[0]))
            for role in roles[1:]:
                asyncio.run(self.store.grant_role(member_id, role, member_id, "test"))
            return ConsoleActor(member_id=member_id, roles=frozenset(roles))

        self.annotator = member("a@x.vn", "ai_annotator")
        self.reviewer = member("r@x.vn", "ai_reviewer")
        self.engineer = member("e@x.vn", "ai_ml_engineer", "ai_data_engineer")
        self.lead = member("l@x.vn", "ai_lead")
        self.lead2 = member("l2@x.vn", "ai_lead")

    def tearDown(self):
        from psycopg2 import sql

        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin_conn.close()

    def _import(self, n, group=None, reasons=("random_audit",), confidence=0.9, machine="51A12345"):
        ids = []
        for i in range(n):
            capture_id = str(uuid4())
            ids.append(capture_id)
            asyncio.run(self.importer.import_batch([ExportedCapture(
                capture_id=capture_id, image_url="http://s/x", image_sha256=SHA, machine_plate=machine,
                machine_confidence=confidence, confirmed_plate="51A12345", human_corrected=False,
                selection_reasons=tuple(reasons), status="PENDING", purpose="train", final_plate="",
                group_ref=hashlib.sha256((group or capture_id).encode()).hexdigest(),
                area_ref="b" * 64, updated_at=f"2026-10-16T01:00:{i:02d}+00:00", captured_at="",
            )]))
        return ids

    def _label_and_approve(self, capture_id, verdict="CORRECT", plate=""):
        asyncio.run(self.lab.add_label(self.annotator, capture_id, verdict, plate))
        item = next(i for i in asyncio.run(self.lab.review_queue(self.reviewer)) if i["capture_id"] == capture_id)
        asyncio.run(self.lab.decide(self.reviewer, item["label"]["id"], "APPROVED"))

    def test_bon_mat_nguoi_gan_khong_duyet_duoc_nhan_cua_minh(self):
        [capture_id] = self._import(1)
        self.assertEqual([capture_id], [s["capture_id"] for s in asyncio.run(self.lab.label_queue(self.annotator))])
        with self.assertRaises(ConsoleAccessDenied):
            asyncio.run(self.lab.review_queue(self.annotator))  # annotator không có quyền duyệt
        label_id = asyncio.run(self.lab.add_label(self.reviewer, capture_id, "CORRECTED", "51a-123.46"))
        # Người gán (reviewer) không thấy nhãn của mình trong hàng duyệt, và tự duyệt bị chặn.
        self.assertEqual([], asyncio.run(self.lab.review_queue(self.reviewer)))
        with self.assertRaises(ConsoleStoreError):
            asyncio.run(self.lab.decide(self.reviewer, label_id, "APPROVED"))
        # Mẫu đang chờ duyệt rời hàng gán.
        self.assertEqual([], asyncio.run(self.lab.label_queue(self.annotator)))
        with self.assertRaisesRegex(ValueError, "lý do"):
            asyncio.run(self.lab.decide(self.lead, label_id, "REJECTED", ""))
        asyncio.run(self.lab.decide(self.lead, label_id, "REJECTED", "sai ký tự cuối"))
        # Bị trả lại → quay về hàng gán cho người KHÁC người đã gán.
        self.assertEqual(1, len(asyncio.run(self.lab.label_queue(self.annotator))))
        actions = [e["action"] for e in asyncio.run(self.store.list_audit(20))]
        self.assertIn("vision.review:REJECTED", actions)

    def test_nap_mau_demo_lap_lai_khong_loi_va_giu_bon_mat(self):
        from app.core.console.engines.demo_plate_generator import DEMO_SAMPLES
        from app.core.console.services.vision_lab_service import ConsoleVisionLabService

        lab = ConsoleVisionLabService(store=self.store, demo_seed_enabled=True)
        first = asyncio.run(lab.seed_demo_samples(self.reviewer))
        self.assertEqual({"seeded_samples": len(DEMO_SAMPLES), "seeded_reviews": 2}, first)
        # Nạp lại khi nhãn mẫu vẫn chờ duyệt: không vướng unique index, không đếm nhãn đã có.
        self.assertEqual({"seeded_samples": len(DEMO_SAMPLES), "seeded_reviews": 0},
                         asyncio.run(lab.seed_demo_samples(self.reviewer)))
        # Nhãn mẫu thuộc người khác người bấm nạp, nên chính người bấm duyệt được.
        queue = asyncio.run(lab.review_queue(self.reviewer))
        self.assertEqual(2, len(queue))
        asyncio.run(lab.decide(self.reviewer, queue[0]["label"]["id"], "APPROVED"))
        self.assertIn("vision.demo_seed", [e["action"] for e in asyncio.run(self.store.list_audit(50))])
        # Nạp lại sau khi một nhãn mẫu đã APPROVED: không chèn nhãn thứ hai cho mẫu đó.
        self.assertEqual(0, asyncio.run(lab.seed_demo_samples(self.reviewer))["seeded_reviews"])

    def test_nap_mau_demo_khi_khong_co_nguoi_khac_thi_bo_nhan(self):
        from psycopg2 import sql

        from app.core.console.services.vision_lab_service import ConsoleVisionLabService

        with self.admin_conn, self.admin_conn.cursor() as cur:
            cur.execute(sql.SQL("UPDATE {}.console_member SET status = 'DISABLED' WHERE id <> %s")
                        .format(sql.Identifier(self.schema)), (self.reviewer.member_id,))
        lab = ConsoleVisionLabService(store=self.store, demo_seed_enabled=True)
        self.assertEqual(0, asyncio.run(lab.seed_demo_samples(self.reviewer))["seeded_reviews"])
        self.assertEqual([], asyncio.run(lab.review_queue(self.reviewer)))

    def test_snapshot_train_loai_nhom_da_vao_golden_da_khoa(self):
        golden_ids = self._import(2, group="phien-1")
        train_ids = self._import(3)
        for capture_id in golden_ids + train_ids:
            self._label_and_approve(capture_id)
        golden = asyncio.run(self.lab.create_snapshot(self.engineer, "golden", "golden v1"))
        self.assertEqual(5, golden["sample_count"])
        with self.assertRaises(ConsoleAccessDenied):
            asyncio.run(self.lab.freeze(self.engineer, golden["id"], "chốt bộ test"))
        asyncio.run(self.lab.freeze(self.lead, golden["id"], "chốt bộ test"))
        with self.assertRaises(ConsoleStoreError):
            asyncio.run(self.lab.freeze(self.lead, golden["id"], "lần hai"))
        # Mọi mẫu đã duyệt đều nằm trong golden đã khoá → train rỗng, không tạo được.
        with self.assertRaisesRegex(ValueError, "at least one"):
            asyncio.run(self.lab.create_snapshot(self.engineer, "train", "train v1"))
        fresh = self._import(2)
        for capture_id in fresh:
            self._label_and_approve(capture_id)
        train = asyncio.run(self.lab.create_snapshot(self.engineer, "train", "train v2"))
        self.assertEqual(2, train["sample_count"])
        manifest = asyncio.run(self.store.get_snapshot(train["id"]))["manifest"]
        self.assertEqual(set(fresh), {s["sample_id"] for s in manifest["samples"]})
        self.assertTrue({s["split"] for s in manifest["samples"]} <= {"train", "val"})

    def test_model_phai_do_tren_golden_khoa_moi_de_xuat_promote_bon_mat(self):
        ids = self._import(3)
        for capture_id in ids:
            self._label_and_approve(capture_id)
        golden = asyncio.run(self.lab.create_snapshot(self.engineer, "golden", "golden v1"))
        model_id = asyncio.run(self.models.register(self.engineer, {
            "name": "anpr-yolo", "version": "2026.10.16", "artifact_key": "models/anpr-yolo/2026.10.16/best.pt",
            "sha256": WEIGHTS,
        }))
        with self.assertRaisesRegex(ValueError, "golden đã khoá"):
            asyncio.run(self.models.start_eval(self.engineer, golden["id"]))
        with self.assertRaisesRegex(ValueError, "Chưa có lượt đo"):
            asyncio.run(self.models.propose(self.engineer, model_id, "tốt hơn bản cũ"))
        asyncio.run(self.lab.freeze(self.lead, golden["id"], "chốt"))

        async def run_eval():
            run_id = await self.models.start_eval(self.engineer, golden["id"])
            await self.models.drain()
            return run_id

        run_id = asyncio.run(run_eval())
        run = next(e for e in asyncio.run(self.store.list_evals()) if e["id"] == run_id)
        self.assertEqual("DONE", run["status"], run["error"])
        self.assertEqual(3, run["metrics"]["total"])

        asyncio.run(self.models.propose(self.lead, model_id, "đo golden v1 đạt"))
        with self.assertRaises(ConsoleAccessDenied):
            asyncio.run(self.models.promote(self.lead, model_id, "tự duyệt"))
        asyncio.run(self.models.promote(self.lead2, model_id, "duyệt"))
        self.assertEqual("production", asyncio.run(self.store.get_model(model_id))["stage"])

        second = asyncio.run(self.models.register(self.engineer, {
            "name": "anpr-yolo", "version": "2026.10.20", "artifact_key": "models/anpr-yolo/2026.10.20/best.pt",
            "sha256": WEIGHTS,
        }))
        asyncio.run(self.models.propose(self.engineer, second, "bản mới"))
        asyncio.run(self.models.promote(self.lead, second, "duyệt"))
        self.assertEqual("retired", asyncio.run(self.store.get_model(model_id))["stage"])
        actions = [e["action"] for e in asyncio.run(self.store.list_audit(50))]
        self.assertTrue({"model.register", "model.propose", "model.promote", "model.retire"} <= set(actions))

    def test_do_chinh_xac_that_chi_tren_random_audit_va_nguong_bon_mat(self):
        right = self._import(18, confidence=0.95)
        wrong = self._import(2, confidence=0.60, machine="99Z99999")
        self._import(5, reasons=("low_confidence",), confidence=0.3, machine="99Z99999")  # không tính
        for capture_id in right + wrong:
            self._label_and_approve(capture_id)
        report = asyncio.run(self.policies.accuracy(self.reviewer))
        self.assertEqual((20, 18, 0.9), (report["total"], report["correct"], report["accuracy"]))
        self.assertEqual({"console": 20, "moderator": 0}, report["truth_sources"])
        self.assertIsNone(report["suggested_threshold"])  # trên 0.60 chỉ có 18 mẫu (< 20)

        created = asyncio.run(self.policies.propose(self.engineer, 0.9, 0.03, "18/18 mẫu ≥ 0.9 đúng"))
        self.assertEqual(1, created["version"])
        with self.assertRaises(ConsoleAccessDenied):
            asyncio.run(self.policies.decide(self.engineer, created["id"], "APPROVED", "tự duyệt"))
        asyncio.run(self.policies.decide(self.lead, created["id"], "APPROVED", "đồng ý"))
        policy = next(p for p in asyncio.run(self.store.list_policies()) if p["id"] == created["id"])
        self.assertEqual(("APPROVED", 18), (policy["status"], policy["evidence"]["at_threshold"]["total"]))
        # Bốn mắt thật: AI Lead có quyền duyệt nhưng không duyệt đề xuất của chính mình.
        own = asyncio.run(self.policies.propose(self.lead, 0.92, 0.03, "nâng ngưỡng"))
        self.assertEqual(2, own["version"])
        with self.assertRaisesRegex(ConsoleStoreError, "tự duyệt"):
            asyncio.run(self.policies.decide(self.lead, own["id"], "APPROVED", "tự duyệt"))

        # ADR-0051: backend chỉ kéo bản đã duyệt; đề xuất chưa duyệt không lọt ra.
        pulled = asyncio.run(self.policies.approved())
        self.assertEqual((created["id"], 1, 0.9, 0.03),
                         (pulled["id"], pulled["version"], pulled["auto_accept_threshold"], pulled["audit_rate"]))
        self.assertTrue(pulled["decided_at"])
        asyncio.run(self.policies.decide(self.lead2, own["id"], "APPROVED", "đồng ý nâng"))
        self.assertEqual(2, asyncio.run(self.policies.approved())["version"])
        self.assertIsNone(asyncio.run(self.policies.approved("vehicle_cls")))

    def test_khoa_golden_qua_http_can_step_up(self):
        import pyotp
        from cryptography.fernet import Fernet
        from fastapi.testclient import TestClient
        from unittest.mock import patch

        from app.console_main import app
        from app.core.console.services import console_auth_service
        from app.core.console.services.vision_lab_service import console_vision_lab_service
        from app.infra.identity.password import hash_password
        from app.infra.identity.totp import TotpVault

        vault = TotpVault(Fernet.generate_key().decode(), "Test")
        secret = vault.new_secret()
        asyncio.run(self.store.create_emergency_admin(
            "lead-http@x.vn", "Lead", hash_password("mật-khẩu-đủ-dài-123"), vault.encrypt(secret), "ai_lead"))
        [capture_id] = self._import(1)
        self._label_and_approve(capture_id)
        golden = asyncio.run(self.lab.create_snapshot(self.engineer, "golden", "golden http"))
        h = {"X-Console-Request": "1"}
        with patch.object(console_auth_service, "store", self.store), \
                patch.object(console_auth_service, "_vault", vault), \
                patch.object(console_vision_lab_service, "store", self.store):
            c = TestClient(app)
            c.post("/console/api/auth/password", json={"email": "lead-http@x.vn", "password": "mật-khẩu-đủ-dài-123"}, headers=h)
            totp = pyotp.TOTP(secret)
            self.assertEqual(200, c.post("/console/api/auth/totp", json={"code": totp.now()}, headers=h).status_code)
            url = f"/console/api/vision/snapshots/{golden['id']}/freeze"
            r = c.post(url, json={"reason": "chốt golden"}, headers=h)
            self.assertEqual((401, "STEP_UP_REQUIRED"), (r.status_code, r.json()["code"]))
            # Mã vừa dùng không dùng lại được: lấy mã của bước thời gian kế tiếp.
            import time
            code = totp.at(time.time() + 30)
            r = c.post("/console/api/auth/step-up", json={"code": code, "reason": "khoá golden"}, headers=h)
            self.assertEqual(200, r.status_code, r.text)
            self.assertEqual(200, c.post(url, json={"reason": "chốt golden"}, headers=h).status_code)
            # AI Lead có quyền duyệt nhãn nên xem được ảnh cắt; trả đúng kiểu ảnh, không cache.
            r = c.get(f"/console/api/vision/samples/{capture_id}/crop")
            self.assertEqual((200, "image/jpeg", "no-store"),
                             (r.status_code, r.headers["content-type"], r.headers["cache-control"]))


if __name__ == "__main__":
    unittest.main()
