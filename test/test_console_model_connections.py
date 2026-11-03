"""ISSUE-022 chặng 2 — connection model LLM: luật SSRF, probe trên HTTP server thật,
rate limit, service, route HTTP, và bảng `ai_model_connections` trên Postgres thật
khi có AI_TEST_DATABASE_URL (IPLMS ADR-0061 §6–§7)."""
import asyncio
import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode
from uuid import uuid4

from app.core.console.dtos import ConsoleActor
from app.core.console.engines.rate_limiter import SlidingWindowLimiter
from app.core.console.guardrails import model_endpoint as guard
from app.core.console.services.model_connection_service import ModelConnectionService
from app.core.exceptions import ConsoleAccessDenied, ConsoleRateLimited, KnowledgeGateError
from app.infra.llm import connection_probe

ML = ConsoleActor("m-ml", frozenset({"ai_ml_engineer"}))
ANALYST = ConsoleActor("m-an", frozenset({"ai_analyst"}))
HOSTS = frozenset({"127.0.0.1", "host.docker.internal", "metadata.test"})
SECRET = "sk-test-khong-duoc-lo-ra-ngoai"


class GuardTest(unittest.TestCase):
    def test_host_ngoai_allowlist_bi_chan(self):
        with self.assertRaises(guard.BlockedEndpoint):
            guard.normalize_base_url("http://evil.example.com/v1", HOSTS)
        with self.assertRaises(guard.BlockedEndpoint):
            guard.normalize_base_url("http://127.0.0.1:11434", frozenset())

    def test_ip_metadata_bi_chan_ke_ca_khi_co_trong_allowlist(self):
        hosts = HOSTS | {"169.254.169.254", "fe80::1", "fd00:ec2::254", "100.100.100.200"}
        for url in ("http://169.254.169.254/latest", "http://[fe80::1]/", "http://[fd00:ec2::254]/",
                    "http://100.100.100.200/"):
            with self.subTest(url=url), self.assertRaises(guard.BlockedEndpoint):
                guard.normalize_base_url(url, hosts)

    def test_dia_chi_phan_giai_bi_chan(self):
        for addresses in (["169.254.169.254"], ["10.0.0.5", "169.254.10.1"], ["::ffff:169.254.169.254"],
                          ["fe80::abcd"], ["0.0.0.0"], ["224.0.0.1"], []):
            with self.subTest(addresses=addresses), self.assertRaises(guard.BlockedEndpoint):
                guard.check_resolved_addresses(addresses)

    def test_loopback_va_dai_rieng_qua_duoc(self):
        # Ollama/llama-server chạy ở loopback hoặc host.docker.internal (dải riêng).
        guard.check_resolved_addresses(["127.0.0.1", "::1", "192.168.65.254", "10.1.2.3"])

    def test_chuan_hoa_va_tu_choi_url_xau(self):
        self.assertEqual("http://127.0.0.1:11434", guard.normalize_base_url(" http://127.0.0.1:11434/ ", HOSTS))
        self.assertEqual("http://host.docker.internal:8005/v1",
                         guard.normalize_base_url("http://HOST.docker.internal:8005/v1/", HOSTS))
        for url in ("ftp://127.0.0.1/", "http://user:pw@127.0.0.1/", "http://127.0.0.1/?key=x",
                    "http://127.0.0.1/#x", "file:///etc/passwd", "http://127.0.0.1:99999/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                guard.normalize_base_url(url, HOSTS)

    def test_ten_secret_theo_luat_da_chot(self):
        self.assertEqual("AI_LLM_KEY_OPENAI", guard.clean_secret_env_name("AI_LLM_KEY_OPENAI", "openai", ""))
        self.assertEqual("AI_LLM_API_KEY", guard.clean_secret_env_name("AI_LLM_API_KEY", "openai", "AI_LLM_API_KEY"))
        self.assertEqual("", guard.clean_secret_env_name("", "ollama", ""))
        for name, provider in (("AI_DATABASE_URL", "ollama"), ("ai_llm_key_x", "openai"),
                               ("", "openai"), ("AI_LLM_KEY_" + "X" * 60, "openai")):
            with self.subTest(name=name), self.assertRaises(ValueError):
                guard.clean_secret_env_name(name, provider, "")

    def test_clean_connection(self):
        values = guard.clean_connection(
            {"name": "  Ollama   máy GPU ", "provider": "ollama", "base_url": "http://127.0.0.1:11434"},
            HOSTS, "",
        )
        self.assertEqual({"name": "Ollama máy GPU", "provider": "ollama",
                          "base_url": "http://127.0.0.1:11434", "secret_env_name": ""}, values)
        with self.assertRaises(ValueError):
            guard.clean_connection({"name": "x", "provider": "ollama", "base_url": "http://127.0.0.1"}, HOSTS, "")
        with self.assertRaises(ValueError):
            guard.clean_connection({"name": "abc", "provider": "anthropic", "base_url": "http://127.0.0.1"}, HOSTS, "")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionError, OSError):
            pass  # client (probe) đã đóng socket vì timeout — đúng kịch bản test

    def do_GET(self):
        server = self.server
        server.hits.append((self.path, self.headers.get("Authorization", "")))
        mode = server.mode
        if mode == "slow":
            time.sleep(3)
        if mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
            self.end_headers()
            return
        if mode == "auth":
            self.send_response(401)
            self.end_headers()
            return
        if self.path == "/api/tags":
            body = {"models": [] if mode == "empty" else [{"name": "qwen2.5:0.5b"}, {"name": "llama3"}]}
        elif self.path == "/v1/models":
            body = {"data": [{"id": "gpt-test"}]}
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ProbeTest(unittest.TestCase):
    """HTTP server thật trên loopback; không gọi ra Internet."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.server.hits, cls.server.mode = [], "ok"
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.server.hits.clear()
        self.server.mode = "ok"
        self.base = f"http://127.0.0.1:{self.port}"

    def _probe(self, provider="ollama", base=None, secret="", timeout=5.0, **kw):
        return connection_probe.probe(provider, base or self.base, secret,
                                      guard.check_resolved_addresses, timeout, **kw)

    def test_ollama_ok_tra_model_va_do_tre(self):
        result = self._probe()
        self.assertTrue(result["ok"], result)
        self.assertEqual(["qwen2.5:0.5b", "llama3"], result["models"])
        self.assertIsInstance(result["latency_ms"], int)
        self.assertEqual("/api/tags", self.server.hits[0][0])

    def test_openai_compat_va_secret_chi_o_header(self):
        with patch.dict(os.environ, {"AI_LLM_KEY_TEST": SECRET}):
            result = self._probe("openai", self.base + "/v1", "AI_LLM_KEY_TEST")
        self.assertTrue(result["ok"], result)
        self.assertEqual(["gpt-test"], result["models"])
        self.assertEqual(("/v1/models", f"Bearer {SECRET}"), self.server.hits[0])
        self.assertNotIn(SECRET, json.dumps(result))

    def test_thieu_bien_secret_khong_gui_request(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_LLM_KEY_MISSING", None)
            result = self._probe("openai", self.base, "AI_LLM_KEY_MISSING")
        self.assertEqual("auth_failed", result["error"])
        self.assertEqual([], self.server.hits)

    def test_sai_xac_thuc(self):
        self.server.mode = "auth"
        self.assertEqual("auth_failed", self._probe()["error"])

    def test_khong_co_model(self):
        self.server.mode = "empty"
        result = self._probe()
        self.assertEqual((False, "no_models"), (result["ok"], result["error"]))

    def test_khong_theo_redirect_toi_metadata(self):
        self.server.mode = "redirect"
        result = self._probe()
        self.assertEqual("unreachable", result["error"])
        self.assertIn("302", result["detail"])
        self.assertEqual(1, len(self.server.hits))

    def test_qua_thoi_gian(self):
        self.server.mode = "slow"
        started = time.monotonic()
        result = self._probe(timeout=0.5)
        self.assertEqual("timeout", result["error"])
        self.assertLess(time.monotonic() - started, 2.5)

    def test_cong_dong(self):
        sock = __import__("socket").socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        self.assertEqual("unreachable", self._probe(base=f"http://127.0.0.1:{port}")["error"])

    def test_dns_tro_ve_link_local_bi_chan_truoc_khi_mo_socket(self):
        # Tên trong allowlist nhưng DNS trả về IP metadata (DNS rebinding).
        result = self._probe(base=f"http://metadata.test:{self.port}",
                             resolve=lambda host, port: ["127.0.0.1", "169.254.169.254"])
        self.assertEqual("blocked_host", result["error"])
        self.assertEqual([], self.server.hits)

    def test_noi_vao_dung_ip_da_kiem(self):
        # Tên lạ phân giải (giả) ra loopback → probe nối vào IP đó, Host header giữ tên gốc.
        result = self._probe(base=f"http://host.docker.internal:{self.port}",
                             resolve=lambda host, port: ["127.0.0.1"])
        self.assertTrue(result["ok"], result)


class RateLimiterTest(unittest.TestCase):
    def test_lan_thu_11_trong_60s_bi_chan(self):
        now = [1000.0]
        limiter = SlidingWindowLimiter(10, 60, clock=lambda: now[0])
        for _ in range(10):
            limiter.hit("m-1")
        with self.assertRaises(ConsoleRateLimited):
            limiter.hit("m-1")
        limiter.hit("m-2")  # đếm riêng từng thành viên
        now[0] += 60.1
        limiter.hit("m-1")


def _row(**over):
    row = {
        "id": str(uuid4()), "name": "Ollama", "provider": "ollama", "base_url": "http://127.0.0.1:11434",
        "secret_env_name": "", "status": "ACTIVE", "replaces_id": "", "created_by": "m-ml",
        "created_at": "2026-10-28T00:00:00+00:00", "disabled_by": "", "disabled_at": "",
        "last_tested_at": "", "last_test_ok": None, "last_test_error": "",
        "last_test_latency_ms": None, "last_test_models": [],
    }
    row.update(over)
    return row


class _Cfg:
    model_connection_hosts = "127.0.0.1,host.docker.internal"
    model_secret_names = ""
    model_test_timeout_seconds = 2.0
    model_tests_per_minute = 10


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.store = AsyncMock()
        self.audit = AsyncMock()
        self.probe_calls = []

        def probe(provider, base_url, secret, check, timeout):
            self.probe_calls.append((provider, base_url, secret))
            return {"ok": True, "error": "", "latency_ms": 5, "models": ["m"], "detail": ""}

        self.service = ModelConnectionService(
            self.store, self.audit, probe, SlidingWindowLimiter(10, 60),
        )
        self.cfg = patch.object(ModelConnectionService, "_cfg", staticmethod(lambda: _Cfg))
        self.cfg.start()

    def tearDown(self):
        self.cfg.stop()

    def test_analyst_chi_xem_khong_ghi(self):
        self.store.list_connections.return_value = []
        asyncio.run(self.service.list_connections(ANALYST))
        for call in (
            self.service.create_connection(ANALYST, {}, "lý do"),
            self.service.disable_connection(ANALYST, str(uuid4()), "lý do"),
            self.service.test_connection(ANALYST, str(uuid4())),
            self.service.test_draft(ANALYST, {}),
        ):
            with self.assertRaises(ConsoleAccessDenied):
                asyncio.run(call)
        self.store.create_connection.assert_not_awaited()

    def test_tao_ghi_audit_chi_ten_secret(self):
        self.store.create_connection.return_value = _row(provider="openai", secret_env_name="AI_LLM_KEY_A")
        with patch.dict(os.environ, {"AI_LLM_KEY_A": SECRET}):
            asyncio.run(self.service.create_connection(
                ML, {"name": "OpenAI", "provider": "openai", "base_url": "http://127.0.0.1:9/v1",
                     "secret_env_name": "AI_LLM_KEY_A"}, "thêm provider",
            ))
        reason = self.audit.add_audit.await_args.args[4]
        self.assertIn("secret_env_name=AI_LLM_KEY_A", reason)
        self.assertNotIn(SECRET, reason)
        self.assertEqual("model.connection_create", self.audit.add_audit.await_args.args[1])

    def test_tao_bat_buoc_ly_do_va_host_trong_allowlist(self):
        with self.assertRaises(ValueError):
            asyncio.run(self.service.create_connection(
                ML, {"name": "Ollama", "provider": "ollama", "base_url": "http://127.0.0.1:11434"}, ""))
        with self.assertRaises(guard.BlockedEndpoint):
            asyncio.run(self.service.create_connection(
                ML, {"name": "Ollama", "provider": "ollama", "base_url": "http://10.0.0.9:11434"}, "lý do"))
        self.store.create_connection.assert_not_awaited()

    def test_thu_ban_nhap_khong_ghi_ai_db(self):
        result = asyncio.run(self.service.test_draft(
            ML, {"name": "Thử", "provider": "ollama", "base_url": "http://127.0.0.1:11434"}))
        self.assertTrue(result["ok"])
        self.assertEqual([], self.store.method_calls)
        self.assertEqual("draft", self.audit.add_audit.await_args.args[3])

    def test_thu_ban_nhap_host_cam_tra_blocked_host_khong_goi_mang(self):
        result = asyncio.run(self.service.test_draft(
            ML, {"provider": "ollama", "base_url": "http://169.254.169.254/"}))
        self.assertEqual("blocked_host", result["error"])
        self.assertEqual([], self.probe_calls)

    def test_thu_connection_da_luu_kiem_lai_allowlist(self):
        # Host từng hợp lệ nhưng đã bị gỡ khỏi allowlist → không gọi mạng.
        row = _row(base_url="http://old-host.internal:11434")
        self.store.get_connection.return_value = row
        result = asyncio.run(self.service.test_connection(ML, row["id"]))
        self.assertEqual("blocked_host", result["error"])
        self.assertEqual([], self.probe_calls)
        self.store.record_connection_test.assert_awaited_once()

    def test_rate_limit_tinh_ca_hai_kieu_thu(self):
        row = _row()
        self.store.get_connection.return_value = row
        draft = {"provider": "ollama", "base_url": "http://127.0.0.1:11434"}
        for i in range(10):
            asyncio.run(self.service.test_draft(ML, draft) if i % 2 else self.service.test_connection(ML, row["id"]))
        with self.assertRaises(ConsoleRateLimited):
            asyncio.run(self.service.test_draft(ML, draft))
        self.assertEqual(10, len(self.probe_calls))

    def test_probe_treo_thi_tra_timeout(self):
        def hang(*args):
            time.sleep(4)

        service = ModelConnectionService(self.store, self.audit, hang, SlidingWindowLimiter(10, 60))
        async def run():
            # Đo trong event loop: route trả lời sau timeout + 1 s, không chờ thread treo.
            started = time.monotonic()
            result = await service.test_draft(ML, {"provider": "ollama", "base_url": "http://127.0.0.1:1"})
            return result, time.monotonic() - started

        result, elapsed = asyncio.run(run())
        self.assertEqual("timeout", result["error"])
        self.assertLess(elapsed, 3.5)


class HttpTest(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient

        from app.console_main import app
        from test.test_console_settings_http import H, _session

        self.client = TestClient(app)
        self.H, self._session = H, _session

    def _as(self, roles):
        from app.core.console import auth_service

        return patch.object(auth_service, "resolve", new_callable=AsyncMock,
                            return_value=self._session(roles))

    def test_quyen_va_429(self):
        from app.core.console import model_connection_service as svc

        ok = {"ok": True, "error": "", "latency_ms": 3, "models": ["m"], "detail": ""}
        limiter = SlidingWindowLimiter(10, 60)
        with patch.object(svc, "_limiter", limiter), \
             patch.object(svc, "_run_probe", new_callable=AsyncMock, return_value=ok), \
             patch.object(svc, "_cfg", staticmethod(lambda: _Cfg)), \
             patch.object(svc.audit, "add_audit", new_callable=AsyncMock):
            body = {"provider": "ollama", "base_url": "http://127.0.0.1:11434"}
            with self._as(("ai_analyst",)):
                self.assertEqual(403, self.client.post("/api/models/connections/test", json=body, headers=self.H).status_code)
            with self._as(("ai_ml_engineer",)):
                codes = [self.client.post("/api/models/connections/test", json=body, headers=self.H).status_code
                         for _ in range(11)]
                last = self.client.post("/api/models/connections/test", json=body, headers=self.H)
        self.assertEqual([200] * 10 + [429], codes)
        self.assertEqual("RATE_LIMITED", last.json()["code"])

    def test_khong_nhan_truong_key(self):
        with self._as(("ai_ml_engineer",)):
            r = self.client.post("/api/models/connections/test",
                                 json={"provider": "openai", "base_url": "http://127.0.0.1", "api_key": SECRET},
                                 headers=self.H)
        self.assertEqual(422, r.status_code)


@unittest.skipUnless(os.getenv("AI_TEST_DATABASE_URL"), "requires AI_TEST_DATABASE_URL")
class ConnectionDatabaseTest(unittest.TestCase):
    """Bảng thật trên Postgres riêng cho test, mỗi lần một schema tạm rồi xoá."""

    def setUp(self):
        import psycopg2
        from psycopg2 import sql

        from app.infra.database.model_policy_store import ModelPolicyStore

        self.psycopg2, self.sql = psycopg2, sql
        base = os.environ["AI_TEST_DATABASE_URL"]
        self.schema = "model_conn_test_" + uuid4().hex
        self.admin = psycopg2.connect(base)
        self.admin.autocommit = True
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.url = base + ("&" if "?" in base else "?") + urlencode({"options": "-csearch_path=" + self.schema})
        self.store = ModelPolicyStore(self.url)

    def tearDown(self):
        with self.admin.cursor() as cur:
            cur.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))
        self.admin.close()

    def _values(self, name="Ollama"):
        return {"name": name, "provider": "ollama", "base_url": "http://127.0.0.1:11434", "secret_env_name": ""}

    def _exec(self, query, params=()):
        with self.psycopg2.connect(self.url) as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall() if cur.description else None

    def test_schema_idempotent_va_khop_ban_chot(self):
        asyncio.run(self.store.ensure_schema())
        self.store._schema_ready = False
        asyncio.run(self.store.ensure_schema())
        cols = {r[0]: (r[1], r[2]) for r in self._exec(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'ai_model_connections'", (self.schema,))}
        self.assertEqual(16, len(cols))
        self.assertEqual(("uuid", "NO"), cols["id"])
        self.assertEqual(("character varying", "YES"), cols["secret_env_name"])
        self.assertEqual(("jsonb", "YES"), cols["last_test_models"])
        self.assertEqual(("timestamp with time zone", "NO"), cols["created_at"])
        indexes = {r[0]: r[1] for r in self._exec(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s AND tablename = 'ai_model_connections'",
            (self.schema,))}
        self.assertIn("uq_ai_model_connections_active_name", indexes)
        self.assertIn("WHERE ((status)::text = 'ACTIVE'::text)", indexes["uq_ai_model_connections_active_name"])

    def test_vong_doi_tao_sua_tat_thu(self):
        first = asyncio.run(self.store.create_connection(self._values(), "m-1"))
        with self.assertRaises(KnowledgeGateError):
            asyncio.run(self.store.create_connection(self._values(), "m-2"))  # trùng tên đang bật
        second = asyncio.run(self.store.create_connection(
            {**self._values(), "base_url": "http://127.0.0.1:11435"}, "m-2", first["id"]))
        self.assertEqual(first["id"], second["replaces_id"])
        old = asyncio.run(self.store.get_connection(first["id"]))
        self.assertEqual(("DISABLED", "m-2"), (old["status"], old["disabled_by"]))
        with self.assertRaises(KnowledgeGateError):
            asyncio.run(self.store.create_connection(self._values("Khác"), "m-2", first["id"]))  # bản đã tắt
        tested = asyncio.run(self.store.record_connection_test(
            second["id"], {"ok": True, "error": "", "latency_ms": 12, "models": ["qwen"]}))
        self.assertEqual((True, 12, ["qwen"]), (tested["last_test_ok"], tested["last_test_latency_ms"],
                                                 tested["last_test_models"]))
        failed = asyncio.run(self.store.record_connection_test(
            second["id"], {"ok": False, "error": "timeout", "latency_ms": None, "models": []}))
        self.assertEqual(("timeout", []), (failed["last_test_error"], failed["last_test_models"]))
        asyncio.run(self.store.disable_connection(second["id"], "m-1"))
        with self.assertRaises(KnowledgeGateError):
            asyncio.run(self.store.disable_connection(second["id"], "m-1"))
        # Tên đã tắt hết thì dùng lại được (unique partial).
        asyncio.run(self.store.create_connection(self._values(), "m-1"))
        self.assertEqual(3, len(asyncio.run(self.store.list_connections())))

    def test_check_constraint_chan_du_lieu_sai(self):
        asyncio.run(self.store.ensure_schema())
        insert = ("INSERT INTO ai_model_connections (id, name, provider, base_url, secret_env_name, status, "
                  "disabled_at, created_by) VALUES (%s, 'n', %s, %s, %s, %s, %s, 'm')")
        bad = [
            ("anthropic", "http://x", None, "ACTIVE", None),
            ("ollama", "ftp://x", None, "ACTIVE", None),
            ("ollama", "http://x", "lower_case", "ACTIVE", None),
            ("ollama", "http://x", None, "DISABLED", None),
            ("ollama", "http://x", None, "ACTIVE", "2026-10-28T00:00:00Z"),
        ]
        for values in bad:
            with self.subTest(values=values), self.assertRaises(self.psycopg2.errors.CheckViolation):
                self._exec(insert, (str(uuid4()), *values))
        self._exec(insert, (str(uuid4()), "ollama", "http://x", None, "ACTIVE", None))
        for update in ("UPDATE ai_model_connections SET last_tested_at = NOW()",  # thiếu last_test_ok
                       "UPDATE ai_model_connections SET last_test_latency_ms = -1",
                       "UPDATE ai_model_connections SET last_test_error = 'other'"):
            with self.subTest(update=update), self.assertRaises(self.psycopg2.errors.CheckViolation):
                self._exec(update)

    def test_explain_q3_dung_unique_partial(self):
        asyncio.run(self.store.ensure_schema())
        for i in range(200):
            self._exec("INSERT INTO ai_model_connections (id, name, provider, base_url, status, disabled_at, created_by) "
                       "VALUES (%s, %s, 'ollama', 'http://x', 'DISABLED', NOW(), 'm')", (str(uuid4()), f"n{i}"))
        self._exec("INSERT INTO ai_model_connections (id, name, provider, base_url, created_by) "
                   "VALUES (%s, 'live', 'ollama', 'http://x', 'm')", (str(uuid4()),))
        self._exec("ANALYZE ai_model_connections")
        with self.psycopg2.connect(self.url) as conn, conn.cursor() as cur:
            cur.execute("SET enable_seqscan = off")
            cur.execute("EXPLAIN SELECT id FROM ai_model_connections WHERE name = 'live' AND status = 'ACTIVE'")
            plan = "\n".join(r[0] for r in cur.fetchall())
        self.assertIn("uq_ai_model_connections_active_name", plan)


if __name__ == "__main__":
    unittest.main()
