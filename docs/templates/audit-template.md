# 🩺 AUDIT-NNN: [Đối tượng quét] vs [Quy ước] (VD: BLL Services vs Mapper §7/§8)

> **Đích:** `docs/projects/audits/MM-YYYY/AUDIT-NNN-slug.md` · **Luật chung** (mã số, bằng chứng `file:line`, ký hiệu): [templates/README](../../../templates/README.md)
> **AUDIT khác PROB và review.** PROB phân tích MỘT vấn đề *trước khi* code; review soi lại MỘT phase vừa xong. AUDIT **quét diện rộng** codebase để đo độ lệch so với MỘT quy ước đã chốt (convention/ADR/practice) → ra danh sách vi phạm phân theo mức độ để giao cho người/agent khác sửa.
> **[MUST] Mọi phát hiện phải kèm `file:line` + lệnh quét tái lập được.** Audit không bằng chứng chỉ là cảm tính — người sửa không tin được, người đọc lại sau không kiểm được.

## 📌 Meta

| | |
|---|---|
| **ID** | AUDIT-NNN |
| **Trạng thái** | 🆕 Mở / 🔍 Đang quét / 📋 Đã báo cáo / 🛠️ Đang khắc phục / ✅ Đóng (0 vi phạm còn lại) / 🗃️ Superseded by AUDIT-XXX |
| **Ngày quét** | YYYY-MM-DD |
| **Người quét** | [Tên / AI] |
| **Phạm vi (Scope)** | [Đường dẫn/module được quét — vd `backend/src/modules/**`] |
| **Quy ước đối chiếu** | [Link doc luật — vd `BACKEND_CONVENTIONS §7/§8`, `ADR-00NN`, `practice/PAT-004`] |
| **Người/agent sẽ sửa** | [Điền khi giao việc] |
| **Tags** | `tag1`, `tag2` |

---

## 1. Luật gốc đang đo (Rule under audit)

<!-- Trích NGUYÊN VĂN [MUST]/[NEVER] đang kiểm, kèm link file:line tới doc luật. Đây là "thước đo" — mọi phát hiện bên dưới phải quy chiếu về đây. -->

> **[MUST/NEVER]** … (trích) — *nguồn: `docs/standards/....md §N`*

**Chuẩn vàng để noi theo:** [`Đường/dẫn/tới/file-mẫu`](…) — *1 dòng vì sao nó đúng chuẩn.*

## 2. Phương pháp quét (Method — tái lập được)

<!-- [MUST] Ghi ĐÚNG lệnh đã chạy để ai cũng quét lại ra cùng con số. -->

```bash
# vd: tìm controller khai báo route prefix không đúng quy ước
grep -rnE "@Controller\(" backend/src/modules --include=*.controller.ts
```

- **Đã quét:** [N file / M method]
- **Tổng phát hiện:** 🔴 [x] phải sửa · 🟡 [y] hợp lệ (liệt kê để xác nhận) · ⚪ [z] xám (người quyết)

## 3. Phát hiện (Findings)

> Phân theo MỨC ĐỘ, không theo file. Mỗi dòng phải có `file:line` bấm được và cột "cách xử lý" đủ để người sửa làm ngay mà không cần hỏi lại.

### 🔴 Nhóm A — Vi phạm, PHẢI sửa

| # | `file:line` | Hiện trạng | Vì sao sai | Cách xử lý (→ đích) |
|---|---|---|---|---|
| A1 | [`Path.cs:NN`](…) | [trích ngắn] | [luật nào bị phạm] | [hành động cụ thể + file đích] |

### 🟡 Nhóm B — Cần xem lại / trùng lặp / lệch nhẹ

| # | `file:line` | Hiện trạng | Đề xuất |
|---|---|---|---|
| B1 | [`Path.cs:NN`](…) | … | … |

### ⚪ Nhóm C — HỢP LỆ (liệt kê để user xác nhận, KHÔNG sửa)

<!-- [MUST] Ghi rõ VÌ SAO được miễn (thuật toán đặc biệt / write-op / computed / đã đúng chuẩn). Miễn mà không nêu lý do = lần quét sau lại bị soi lại. -->

| `file:line` | Chỗ | Vì sao được miễn |
|---|---|---|
| [`Path.cs:NN`](…) | … | … |

## 4. Việc giao cho người/agent sửa (Remediation handoff)

<!-- Viết như checklist đứng một mình — người sửa KHÔNG có context chat này. -->

1. [Bước theo Nhóm A/B — nêu rõ tạo/sửa file nào, đăng ký ở đâu nếu cần]
2. **Verify:** [lệnh build/test + kỳ vọng — vd `dotnet build` xanh, `grep ... | wc -l` = 0]
3. **Commit** từng đơn vị một (**[NEVER]** `git add .`), message ghi rõ phạm vi.

## 5. Kiểm tra tuân thủ lại (Re-scan / Compliance check)

<!-- Chạy LẠI đúng lệnh mục 2 sau khi sửa. Audit chỉ ✅ Đóng khi con số về kỳ vọng. -->

```bash
# kỳ vọng sau khắc phục = 0 (hoặc = số Nhóm C được miễn)
<lệnh quét ở mục 2> | wc -l
```
- **Lúc quét:** [x vi phạm] · **Kỳ vọng sau sửa:** [y]

## 6. Liên kết (Link hai chiều)

<!-- Audit sinh ra từ đâu, đẻ ra việc gì — [MUST] link hai chiều (README rule 6). -->
- Sinh ra từ: [PROB-/IDEA-/yêu cầu chat …]
- Đẻ ra: [ISSUE-NNN / bug-NNN thực thi khắc phục — link khi tạo]
