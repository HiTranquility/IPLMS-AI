# 🩺 AUDIT-007: Thay đổi vào develop ngày 27/10/2026 vs AI_CONVENTIONS, ui/DESIGN và ADR-0029

> **Đích:** `docs/projects/audits/10-2026/AUDIT-007-develop-2026-10-27-console-knowledge-settings.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **ID** | AUDIT-007 |
| **Trạng thái** | 📋 Đã báo cáo |
| **Ngày quét** | 2026-10-27 |
| **Người quét** | Claude Code, một lượt (không chạy auditor độc lập, không có vòng 2) |
| **Phạm vi (Scope)** | `git diff 24512ba..e732250` trên `ai/` (develop sáng 27/10 → sau PR #106): 91 file code, +4095/−520. Gồm trang Knowledge và RAG đa lượt (#91), ISSUE-021 (#92), bug-033 đến bug-038 |
| **Quy ước đối chiếu** | [AI_CONVENTIONS](../../../standards/AI_CONVENTIONS.md) §2–§6; [ui/DESIGN.md](../../../../ui/DESIGN.md) luật 8 (màu qua token); IPLMS ADR-0029 (guardrail LLM: đầu vào độc mặc định) |
| **Người/agent sẽ sửa** | Chưa giao |
| **Tags** | `ui-token`, `a11y`, `guardrail`, `rbac` |

## 1. Luật gốc đang đo

> **Luật 8:** "Màu/font chỉ qua token; mỗi theme có `--color-accent-ink`" — chỉ ba ngoại lệ được nêu tên (logo Google, `RoleBadge`, `AuditActionBadge`). *Nguồn: `ui/DESIGN.md:80-82`*

> **ADR-0029:** LLM không cầm quyền, **đầu vào độc mặc định**, đầu ra qua kiểm tất định. *Nguồn: `AGENTS.md` mục Stack, IPLMS ADR-0029*

> **[NEVER]** `app/api/` import thẳng `engines/`; `app/core/` import `grpc`/`_pb2`; đọc `os.environ` rải rác trong engine/service. *Nguồn: `AI_CONVENTIONS.md:34-35, :111`*

**Chuẩn vàng:** `ui/src/pages/Vision/ReviewPage.module.css`, chỉ dùng `var(--color-*)`, không có màu hex.

## 2. Phương pháp quét

```bash
# Máy quét convention của repo, chỉ soi phần diff
python -X utf8 ../script/audit/check_diff.py --root . --range 24512ba...e732250
# Luật kiến trúc AI_CONVENTIONS trên phần diff
git diff 24512ba e732250 -- app/api  | grep -E "^\+.*import.*engines"
git diff 24512ba e732250 -- app/core | grep -E "^\+.*(import grpc|_pb2|generated)"
git diff 24512ba e732250 -- app/core app/infra | grep -E "^\+.*os\.(environ|getenv)"
# Màu ghi cứng trong trang mới, so với các trang còn lại
grep -cE '#[0-9a-fA-F]{3,8}\b|rgba?\(' ui/src/pages/Knowledge/**/*.{tsx,css}
grep -rlE "color: ?'#|color=\"#" ui/src/pages --include=*.tsx | grep -v Knowledge
# Đường đi của history: chỗ nào kiểm, chỗ nào đưa vào LLM
grep -n "check_input\|history" app/core/copilot/engines/rag_pipeline.py app/infra/llm/llm_factory.py
```

Độ tương phản tính theo công thức WCAG 2.x (độ sáng tương đối), nền trắng của theme sáng.

- **Đã quét:** 91 file. Đọc tay `console_tools_controller.py`, `tools_service.py`, `llama_server_manager.py`, `llm_factory.py` (phần stream), `rag_pipeline.py`, `KnowledgePage.tsx`, `DocumentPreviewDrawer.tsx`, `SettingsPage.tsx` (phần phiên).
- **Máy quét:** `check_diff` 0 FAIL / 0 WARN. Ba luật kiến trúc ở trên đều 0 vi phạm.
- **Không áp được:** `script/audit/check_i18n_keys.py` viết cho layout `frontend/packages/shared/src/locales` nên báo `FileNotFoundError` với `ai/ui`. Phần i18n của `ai/ui` do test `noHardcodedVi` và test parity trong vitest giữ (100/100 pass sau bug-038).
- **Tổng phát hiện:** 🔴 2 phải sửa · 🟡 7 cần xem · ⚪ 3 hợp lệ.

## 3. Phát hiện

### 🔴 Nhóm A — Vi phạm, phải sửa

| # | `file:line` | Hiện trạng | Vì sao sai | Cách xử lý |
|---|---|---|---|---|
| A1 | `ui/src/pages/Knowledge/KnowledgePage.tsx:264, 274, 279, 333, 339, 347, 349, 389, 407, 413, 447, 454`; `KnowledgePage.module.css` (53 chỗ); `components/DocumentPreviewDrawer.module.css` (38 chỗ); `DocumentPreviewDrawer.tsx` (2 chỗ) | 110 màu hex/rgba ghi cứng theo bảng slate/emerald của theme tối, ví dụ `color: '#94a3b8'`, `color: '#34d399'` trên `rgba(16,185,129,0.1)`. Các trang khác của `ui/src/pages` có 0 chỗ | Phạm luật 8 của `ui/DESIGN.md`. Ở theme sáng chữ không đọc được: `#34d399` trên nền xanh nhạt đạt **1.75:1**, `#60a5fa` 2.26:1, `#94a3b8` 2.56:1, `#10b981` 2.54:1, dưới ngưỡng 4.5:1 | Thay bằng token có sẵn trong `ui/src/index.css`: `--color-muted`, `--color-success`/`--color-success-soft`, `--color-danger`/`--color-danger-soft`, `--color-info`, `--color-accent-dark`. Dời `style={{}}` sang module CSS. **bug-039** |
| A2 | `app/api/rest/routes/console_tools_controller.py:117-120, 132`; `app/core/copilot/engines/rag_pipeline.py:377`; `app/infra/llm/llm_factory.py:421-427` | `AskIn.history` nhận tối đa 10 lượt × 4000 ký tự, role `user`/`assistant` do client tự khai. `check_input` chỉ chạy trên `query_text`, còn 4 lượt history cuối được nối thẳng vào `messages` gửi LLM. Lượt `assistant` giả mạo cũng được chấp nhận | Phạm ADR-0029 "đầu vào độc mặc định": nội dung history không qua rào chắn injection nào. Rủi ro giới hạn ở console nội bộ (cần `ai:prompt:edit` hoặc `ai:chatlog:read`); gateway công khai `/api/copilot/*` không nhận `history` | Chạy `guardrail_manager.check_input` cho từng `content` trong history (hoặc bỏ lượt không an toàn), và cân nhắc chỉ nhận history do server lưu thay vì client gửi. Chạy lại bộ tấn công guard. **bug-040** |

### 🟡 Nhóm B — Cần xem lại / lệch nhẹ

| # | `file:line` | Hiện trạng | Đề xuất |
|---|---|---|---|
| B1 | `app/core/console/services/tools_service.py:807, 820` | Quyền xem và thu hồi phiên của **người khác** quyết bằng tên vai `{"ai_console_admin", "ai_lead"}`, không qua ma trận quyền. Service cũng không gọi `access_policy` như các method bên cạnh | Đổi sang `access_policy.can(actor, "ai:member:manage")` (hoặc một quyền mới `ai:session:manage`) để ma trận quyền là nguồn duy nhất. Phạm vi "chỉ phiên của mình" ở `console_store.py:698` thì đúng |
| B2 | `app/api/rest/routes/console_tools_controller.py:320`; `app/infra/llm/llama_server_manager.py:57-67` | Pattern của `llm_model` là `^[A-Za-z0-9._:/-]+$`, cho phép `../`. `_resolve_model_path` ghép thẳng vào `model/checkpoint/llm/` mà không kiểm đường dẫn sau khi resolve còn nằm trong thư mục đó | Kiểm `resolved.is_relative_to(gguf_dir)`, hoặc chỉ nhận tên có trong `_detect_available_models`. `Popen` dùng dạng list nên không có shell injection, mức độ thấp |
| B3 | `app/infra/llm/llama_server_manager.py:115` | `atexit.register(self.stop_server)` chạy lại mỗi lần khởi động server (mỗi lần "Nạp lại LLM") | Đăng ký một lần trong `__init__` |
| B4 | `app/core/console/services/tools_service.py:633, 778` | Người chỉ có `ai:prompt:edit` (soạn prompt) vẫn đổi được cấu hình GPU/LLM và gỡ model Vision của process console, không cần step-up TOTP như khoá golden hay promote | **OPEN-01** cho techlead: các thao tác này có cần step-up hoặc quyền riêng không |
| B5 | `ui/src/pages/Knowledge/components/DocumentPreviewDrawer.tsx:28-35, 59-65` | Có `role="dialog"` và `aria-modal="true"`, đóng được bằng Escape, nhưng không chuyển focus vào drawer khi mở, không giữ focus trong drawer, không trả focus về nút đã mở khi đóng | Focus nút đóng khi mở, trả focus khi đóng; tái dùng cách làm của `PersonaSwitcher` hoặc modal sẵn có |
| B6 | `ui/src/pages/Settings/SettingsPage.tsx:841` | Thu hồi phiên dùng `window.confirm`, chỗ duy nhất trong `ui/src`. Trang Knowledge (`KnowledgePage.tsx:561-575`) lại xác nhận ngay trên dòng | Thống nhất một kiểu xác nhận trên dòng: `window.confirm` không theo theme, không có i18n nút, và bị chặn trong một số khung nhúng |
| B7 | `ui/src/pages/Knowledge/KnowledgePage.tsx:321` | Ô chọn file chỉ lọc đuôi file, không kiểm dung lượng so với `KNOWLEDGE_MAX_FILE_BYTES` = 8 MB (`app/core/constants.py:34`). Người dùng chỉ biết file quá lớn sau khi đã tải lên xong | Kiểm dung lượng ngay khi chọn hoặc kéo-thả, báo bằng chữ trên dòng file |

### ⚪ Nhóm C — Hợp lệ (không sửa)

| # | Phạm vi | Vì sao hợp lệ |
|---|---|---|
| C1 | `except Exception` ở `tools_service.py`, `document_parser.py`, `llm_factory.py`, `llama_server_manager.py` | Cách viết chung của codebase cho đường dò phần cứng/dò engine tuỳ chọn; phần lớn có `noqa: BLE001` kèm lý do hoặc ném lại thành `RagPipelineError` |
| C2 | Luật kiến trúc `AI_CONVENTIONS.md:34-35, :111` | 0 chỗ `api → engines`, 0 chỗ `core → grpc`, 0 chỗ `os.environ` mới |
| C3 | Thu hồi phiên của chính mình (`console_store.py:698`) | Có `AND member_id = %s` nên người không phải admin không đụng được phiên người khác |

## 4. Bug và việc mở từ audit

| Mã | Mức | Nội dung | Trạng thái |
|---|---|---|---|
| [bug-039](../../bugs/bug-039-trang-knowledge-mau-ghi-cung-vo-tuong-phan-theme-sang/bug.md) | 🟠 | A1: trang Knowledge ghi cứng 110 màu, theme sáng tương phản 1.75–2.56:1 | 🆕 New |
| [bug-040](../../bugs/bug-040-history-copilot-khong-qua-rao-chan-dau-vao/bug.md) | 🟠 | A2: history Copilot không qua rào chắn đầu vào | 🆕 New |
| OPEN-01 | — | B4: thao tác engine/cấu hình phần cứng có cần step-up không | Chờ techlead |
| (bug-038 ghi chú) | 🟡 | Hai test `no_context` phụ thuộc `.env.dev` bật demo seed | Chưa mở hồ sơ |

## 5. Sơ đồ

Không vẽ: audit này đo độ lệch trên các file có sẵn, không đổi luồng, dữ liệu hay module nào. Luồng của A2 đã mô tả đủ bằng ba `file:line` ở bảng A.

## 6. Đề xuất cải tiến UX

Mỗi đề xuất đều có điểm neo trong code develop `e732250`. Đề xuất lớn thì hỏi trước khi làm.

| # | Ưu tiên | Đề xuất | Điểm neo | Được | Mất |
|---|---|---|---|---|---|
| S1 | Cao | Trang Model báo rõ khi engine Vision chưa nạp weights thật hoặc đang chạy weights giả, bằng component `SimulatedBanner` đã có | `ui/src/components/common/Ui/feedback/SimulatedBanner.tsx:10`; `ModelsPage.tsx` chưa dùng; trạng thái engine đã có ở `tools_service.system_check` (`engines`) | Người audit không hiểu nhầm kết quả 5%/0% trên golden là model hỏng | Cần đưa cờ "weights giả/chưa nạp" ra API Vision, nếu `engines` chưa đủ thông tin |
| S2 | Cao | Thêm dòng nhắc "Tối thiểu 3 ký tự" dưới ô lý do trả lại nhãn (SUGGESTION-007, phản hồi audit PH-02) | `ui/src/pages/Vision/components/ReviewRow.tsx:130-136` (`minLength={3}`, không có hint) | Người mới biết vì sao nút bị khoá | Thêm một key i18n VI/EN |
| S3 | Trung bình | Số "Hàng đợi chờ duyệt" lấy tổng thật từ server, không đếm số dòng đã tải | `ReviewPage.tsx:162` hiện `items.length`; `vision.endpoint.ts:60` chỉ tải 20 dòng; server đã đếm `pending_review` (`console_vision_store.label_counts`) | Khi có hơn 20 nhãn chờ, duyệt xong số đếm vẫn giảm đúng | `/vision/reviews` phải trả thêm tổng, hoặc reviewer cần quyền đọc `status` |
| S4 | Trung bình | Kiểm dung lượng (8 MB) và đuôi file ngay khi chọn hoặc kéo-thả, báo lỗi trên từng dòng file (AUDIT B7) | `KnowledgePage.tsx:321`; `app/core/constants.py:34` | Không phải đợi tải lên xong mới biết file bị từ chối | Giới hạn phải giữ đồng bộ giữa UI và server |
| S5 | Trung bình | Một kiểu xác nhận trên dòng và một drawer/dialog dùng chung có quản lý focus, thay `window.confirm` và drawer tự viết (AUDIT B5, B6) | `SettingsPage.tsx:841`; `KnowledgePage.tsx:561-575`; `DocumentPreviewDrawer.tsx:28-65` | Hành vi nhất quán, dùng được bằng bàn phím, có i18n | Refactor 2–3 chỗ; cần test focus |
| S6 | Thấp | Nút engine trong Settings (nạp sẵn/giải phóng Vision, nạp lại LLM) ghi rõ phạm vi ảnh hưởng, người và lúc thao tác gần nhất (lấy từ audit), và xác nhận trước khi giải phóng | `SettingsPage.tsx:164, 351-360`; audit `engine.*` đã có tên hiển thị (bug-038) | Bớt bấm nhầm, ai cũng biết model vừa bị gỡ là do ai | Thêm một truy vấn audit nhỏ trên trang Settings |
