"""Mock /console/api cho việc xem UI ai/ui cục bộ (dữ liệu giả, không auth thật).
MOCK_MODE=anon -> /me trả 401; admin (mặc định) -> đủ quyền; annotator -> chỉ ai:task:label.
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

MODE = os.environ.get("MOCK_MODE", "admin")
ALL = ["ai:metrics:read","ai:task:label","ai:label:approve","ai:chatlog:read","ai:pii:reveal","ai:pipeline:manage",
       "ai:dataset:snapshot","ai:golden:freeze","ai:model:evaluate","ai:model:propose","ai:model:promote",
       "ai:prompt:edit","ai:policy:threshold","ai:member:manage","ai:audit:read"]
ROLES = ["ai_analyst","ai_annotator","ai_reviewer","ai_data_engineer","ai_ml_engineer","ai_lead","ai_console_admin"]

def me():
    if MODE == "annotator":
        return {"member_id":"m2","email":"annotator@test.local","display_name":"Test Annotator","roles":["ai_annotator"],
                "permissions":["ai:task:label"],"mfa_done":True,"totp_enabled":True,"totp_pending":False}
    return {"member_id":"m1","email":"admin@test.local","display_name":"Test Admin","roles":ROLES,
            "permissions":ALL,"mfa_done":True,"totp_enabled":True,"totp_pending":False}

days = [{"date":f"2026-10-{d:02d}","requests":20+d,"errors":d%3,"refused":d%4,"avg_latency_ms":800+d*20,"speed_tok_s":30} for d in range(10,24)]
usage = {"window_days":14,"total_requests":500,"success_requests":430,"refused_requests":30,"no_context_requests":25,
         "error_requests":15,"avg_latency_ms":950,"p95_latency_ms":2400,"avg_speed_tok_s":31,"input_tokens":120000,
         "output_tokens":40000,"cost_known":False,"total_cost_usd":0,"avg_cost_usd":0,"thumbs_up":40,"thumbs_down":7,"days":days}
stats = {"window_days":14,"reviewed":40,"correct":31,"incorrect":6,"unsafe":3,"accuracy":0.775}
turns = [{"turn_id":f"t{i}","at":f"2026-10-2{i%3}T0{i%9}:15:00Z","task":"copilot","status":["SUCCESS","REFUSED","NO_CONTEXT","ERROR"][i%4],
          "model":"qwen2.5-7b","prompt_version":"v3","input_tokens":300,"output_tokens":120,"latency_ms":900+i*10,"cost_usd":None,
          "user_role":"member","parking_lot_id":"lot-1","query":f"Phí gửi xe qua đêm ở bãi số {i} là bao nhiêu? SĐT tôi [PHONE]",
          "answer":"Theo bảng giá, phí qua đêm là 30.000đ.","error_code":"" if i%4!=3 else "LLM_TIMEOUT",
          "feedback":[1,-1,None][i%3],"review":None} for i in range(12)]
sample = lambda i: {"capture_id":f"cap-{i}","image_sha256":"ab"*32,"machine_plate":"51G-123.45","machine_confidence":0.62+i*0.03,
          "confirmed_plate":"","human_corrected":False,"selection_reasons":["low_confidence"],"source_status":"CONFIRMED",
          "purpose":"audit","source_final_plate":"51G-123.45","group_ref":"g1","area_ref":"a1",
          "captured_at":"2026-10-22T08:00:00Z","source_updated_at":None,"imported_at":"2026-10-22T09:00:00Z"}
curve = [{"threshold":t/100,"total":200-t,"accuracy":0.8+t/1000,"coverage":1-t/120} for t in range(50,100,5)]
ROUTES = {
    "/me": lambda: [me()],
    "/copilot/usage": lambda: [usage], "/copilot/review-stats": lambda: [stats], "/copilot/turns": lambda: turns,
    "/members": lambda: [{"id":"m1","email":"admin@test.local","display_name":"Test Admin","status":"ACTIVE","created_at":"2026-10-01T00:00:00Z","roles":ROLES},
                         {"id":"m2","email":"annotator@test.local","display_name":"Test Annotator","status":"INVITED","created_at":"2026-10-05T00:00:00Z","roles":["ai_annotator"]}],
    "/audit": lambda: [{"id":f"a{i}","actor_id":"m1","action":["role.grant","member.invite","label.decide","policy.propose"][i%4],
                        "target_type":"member","target_id":"m2","reason":"Mở quyền gán nhãn","at":"2026-10-22T10:00:00Z"} for i in range(30)],
    "/tools/system": lambda: [{"checks":[{"key":"llm","label":"LLM","ok":True},{"key":"console_database","label":"Console DB","ok":True},{"key":"rag","label":"RAG","ok":False}],
                               "llm_model":"qwen2.5-7b","telemetry_enabled":True,"vision_device":"cpu","telemetry_retention_days":30,"vision_retention_days":90}],
    "/vision/status": lambda: [{"sample_count":120,"last_imported_at":"2026-10-22T09:00:00Z","watermark_at":"2026-10-22T08:59:00Z",
                                "recent_errors":[{"capture_id":"cap-x","reason":"CROP_MISSING","at":"2026-10-22T09:00:00Z"}],
                                "samples":120,"pending_review":8,"approved":70,"rejected":5}],
    "/vision/queue": lambda: [sample(i) for i in range(5)],
    "/vision/reviews": lambda: [dict(sample(i), label={"id":f"l{i}","verdict":"CORRECTED","plate_text":"51G-123.46","labeler":"Test Annotator","created_at":"2026-10-22T10:00:00Z"}) for i in range(3)],
    "/vision/snapshots": lambda: [{"id":"s1","kind":"golden","name":"golden-oct","samples_sha256":"cd"*32,"sample_count":150,"created_by":"Test Admin",
                                   "created_at":"2026-10-20T00:00:00Z","frozen_by":"","frozen_at":None}],
    "/vision/models": lambda: [{"id":"mv1","name":"anpr-ocr","version":"1.2.0","artifact_key":"models/anpr/1.2.0.pt","sha256":"ef"*32,"train_snapshot_id":"s0",
                                "stage":"candidate","note":"","registered_by":"Test Admin","registered_at":"2026-10-20T00:00:00Z","proposed_by_id":"","proposed_by":"",
                                "proposed_at":None,"approved_by":"","approved_at":None}],
    "/vision/evals": lambda: [{"id":"e1","kind":"golden","snapshot_id":"s1","snapshot_name":"golden-oct","engine_version":"1.2.0",
                               "metrics":{"total":150,"exact_match_strict":0.81,"exact_match_relaxed":0.86,"mean_cer":0.04,"errors":0},
                               "status":"DONE","error":"","started_by":"Test Admin","started_at":"2026-10-21T00:00:00Z","finished_at":"2026-10-21T00:05:00Z"}],
    "/vision/accuracy": lambda: [{"total":200,"correct":170,"accuracy":0.85,"interval_95":[0.8,0.89],"target":0.95,"min_samples":100,
                                  "buckets":[{"from":0.5,"to":0.7,"total":50,"correct":30,"accuracy":0.6},{"from":0.7,"to":1.0,"total":150,"correct":140,"accuracy":0.93}],
                                  "curve":curve,"suggested_threshold":0.9,"suggestion_reason":"Đạt 95% trên 120 mẫu","truth_sources":{"console":120,"moderator":80}}],
    "/vision/policies": lambda: [{"id":"p1","model_name":"anpr-ocr","version":1,"auto_accept_threshold":0.9,"audit_rate":0.05,"status":"PROPOSED",
                                  "evidence":{"audit_total":200,"audit_accuracy":0.85},"reason":"Ngưỡng mới","proposed_by":"Test Admin","proposed_by_id":"m1",
                                  "proposed_at":"2026-10-22T00:00:00Z","decided_by":"","decided_at":None}],
}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw)))
        self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path = urlparse(self.path).path.removeprefix("/console/api")
        if path == "/me" and MODE == "anon":
            return self._send(401, {"success":False,"message":"Chưa đăng nhập.","code":"UNAUTHENTICATED","data":[]})
        if path.endswith("/crop"):
            self.send_response(404); self.end_headers(); return
        fn = ROUTES.get(path)
        if fn is None:
            return self._send(404, {"success":False,"message":"Không tìm thấy.","code":"NOT_FOUND","data":[]})
        self._send(200, {"success":True,"message":"OK","data":fn()})
    def do_POST(self):
        path = urlparse(self.path).path.removeprefix("/console/api")
        n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
        if path == "/tools/copilot":
            return self._send(200, {"success":True,"message":"OK","data":[{"answer":"Phí qua đêm 30.000đ.","sources":["bang-gia.md"],"confidence":0.81,
                                    "model_revision":"r1","turn_id":"tx","prompt_version":"v3"}]})
        if path.endswith("/freeze") or path.endswith("/promote") or path == "/vision/seed-demo":
            return self._send(403, {"success":False,"message":"Thao tác này cần nhập lại mã TOTP kèm lý do.","code":"STEP_UP_REQUIRED","data":[]})
        self._send(200, {"success":True,"message":"OK","data":[{"ok":True,"id":"new","changed":True,"mfa_required":False,"seeded_samples":0,"seeded_reviews":0}]})
    def log_message(self, *a):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

ThreadingHTTPServer(("127.0.0.1", 8090), H).serve_forever()
