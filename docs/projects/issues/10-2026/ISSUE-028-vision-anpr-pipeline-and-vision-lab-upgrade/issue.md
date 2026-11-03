# 🏷️ ISSUE-028: Nâng cấp pipeline ANPR (tiền xử lý, hậu xử lý biển số) và Vision Lab trên AI Console

> **Đích:** `docs/projects/issues/10-2026/ISSUE-028-vision-anpr-pipeline-and-vision-lab-upgrade/issue.md` · **Luật chung:** [templates/README](../../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Done |
| **Người phụ trách** | Dương (@23110012) |
| **Phạm vi** | `ai/`: `app/core/vision/engines/anpr/`, `ui/src/pages/Vision/`, `test/` |
| **Nhánh** | `feature/ISSUE-020-2026-10-vision-anpr-pipeline-and-vision-lab-upgrade` |
| **Bắt nguồn từ** | [ISSUE-018](../ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) dòng 33 (chủ dự án giao 2026-10-26) |
| **Người nhận** | Dương |
| **Hạn** | — |
| **Ưu tiên** | 🟠 |
| **Ngày tạo** | 2026-10-26 |
| **Ngày đóng** | 2026-10-26 |

## Mục tiêu

Nâng cấp toàn diện phần **Vision ANPR pipeline** và **Vision Lab trên AI Console** do Dương phụ trách từ 2026-10-26 theo phân công tại [ISSUE-018](../ISSUE-018-ke-hoach-theo-thanh-vien/issue.md):
1. **Chốt phạm vi & chỉ số đo (Metrics) trước khi code:**
   - **Exact-Match Strict (`exact_strict`):** Tỷ lệ chuỗi biển số nhận diện khớp nguyên văn nhãn chuẩn (kể cả dấu gạch ngang `-` và dấu chấm `.`), tính bằng `training.plate_metrics.normalize_strict`.
   - **Exact-Match Relaxed (`exact_relaxed`):** Tỷ lệ chuỗi biển số khớp toàn bộ ký tự chữ và số sau khi lược bỏ dấu phân cách (`-`, `.`, khoảng trắng), tính bằng `training.plate_metrics.normalize_relaxed` / `plate_key`.
   - **Character Error Rate (`CER`):** Khoảng cách chỉnh sửa Levenshtein trên khóa `relaxed` chia cho độ dài nhãn thật (`levenshtein(truth_relaxed, pred_relaxed) / len(truth_relaxed)`), phản ánh chính xác mức sai lệch ký tự OCR.
   - **Cờ chất lượng ảnh (`quality_flags`):** Chẩn đoán tất định điều kiện ảnh biên (`blurry`, `glare`, `skewed`, `two_line`) phục vụ tiền xử lý thích nghi và lọc kiểm duyệt 4 mắt.
   - **Ranh giới an toàn:** Không tự ý thay đổi/ghi đè file checkpoint trong `model/` hoặc `data/` khi chưa có phê duyệt của chủ dự án (`AGENTS.md`); giữ nguyên hợp đồng `sanitize_plate_text` không tự chèn dấu gạch ngang làm lệch truy vấn biển số của backend.
2. **Nâng cấp tầng tiền xử lý & hậu xử lý ANPR (`app/core/vision/engines/anpr/`):**
   - Bổ sung `assess_crop_quality(crop)` và `suppress_glare_for_ocr(crop)` trong `preprocess.py` để phát hiện ảnh mờ (`blurry`), chói đèn pha (`glare`), nghiêng (`skewed`), biển 2 dòng (`two_line`) và nén vùng cháy sáng trên kênh L (không gian LAB) trước khi chạy CLAHE + OCR.
   - Nâng cấp `correct_plate_confusions(text)` trong `plate_text.py` để sửa nhầm chữ–số cho **cả 5 chữ số cuối** trên biển 5 số (biển 1 dòng 8 ký tự `51H-123.45` và biển 2 dòng 9 ký tự `59-K1 123.45`, `59-AA 123.45`), đồng thời giữ an toàn cho biển 4 số cũ (`51H-1234`, `50-N1 6789`, `51LD-1234`).
   - Bổ sung hàm định dạng tường minh `format_vietnam_plate(text, is_two_line=False)` cho hiển thị chuẩn Việt Nam (`XXY-NNN.NN` hoặc `XX-YZ NNN.NN`).
   - Tích hợp `assess_crop_quality` và `suppress_glare_for_ocr` vào nhánh làm nét (`enhanced`) của `anpr_engine.py` khi ảnh cắt bị chói sáng (`glare`) chưa có định dạng mạnh.
3. **Nâng cấp Vision Lab trên AI Console (`ui/src/pages/Vision/`):**
   - Bổ sung bộ lọc theo **cờ điều kiện ảnh (`quality_flags`)** trên trang Duyệt nhãn 4 mắt (`ReviewPage.tsx`) giúp Reviewer lọc nhanh các ca biên (`blurry`, `glare`, `skewed`, `occluded`, `two_line`) song song với bộ lọc `Tất cả / Khớp 100% / Đã sửa`.

## 📋 Việc trên BOARD

| Việc | Người nhận | Hạn | Ưu tiên | Trạng thái | Ghi chú |
|---|---|---|---|---|---|
| Chốt phạm vi, chỉ số đo (Strict, Relaxed, CER) và nâng cấp pipeline ANPR (`preprocess.py`, `plate_text.py`, `anpr_engine.py`) + bộ lọc cờ chất lượng ảnh trên Vision Lab (`ReviewPage.tsx`) kèm unit test Python & Vitest | Dương | — | 🟠 | ✅ Done | Từ ISSUE-018 dòng 33; 87/87 unittest ANPR PASS, Vitest Vision PASS |

## Tiêu chí chấp nhận

- [x] Hồ sơ `ISSUE-028` định nghĩa rõ phạm vi, chỉ số đo (`exact_strict`, `exact_relaxed`, `cer`, `quality_flags`) và ranh giới không đụng checkpoint `model/`.
- [x] `app/core/vision/engines/anpr/preprocess.py`: có `assess_crop_quality(crop)` và `suppress_glare_for_ocr(crop)` hoạt động tất định, không làm biến đổi mảng ảnh gốc (`evidence_image`).
- [x] `app/core/vision/engines/anpr/plate_text.py`: `correct_plate_confusions` sửa được chữ số thứ 5 từ cuối trên biển 5 số (8–9 ký tự chữ-số) mà không làm hỏng chữ cái sê-ri của biển 4 số; có `format_vietnam_plate`.
- [x] `ui/src/pages/Vision/ReviewPage.tsx`: lọc được hàng đợi duyệt 4 mắt theo từng cờ `quality_flags` (`blurry`, `glare`, `skewed`, `occluded`, `two_line`), có `role="group"` và `aria-pressed`.
- [x] Toàn bộ unit test hiện có và mới (`test_plate_text`, `test_plate_metrics`, `test_vision_optimizations`, `test_two_line_plate_parser`, `test_anpr_pipeline`, `test_anpr_pipeline_upgrade`, và `ReviewRowNames.test.tsx` / `Vision.test.tsx`) đều PASS; `tsc --noEmit` và `check_generated.py` PASS.

## Kế hoạch

1. Lập hồ sơ `ISSUE-020` và kiểm tra `check_branch_policy.py` (PASS).
2. Cải tiến `preprocess.py`, `plate_text.py`, `anpr_engine.py` và viết bộ test `test/test_anpr_pipeline_upgrade.py` (87/87 PASS).
3. Cải tiến `ReviewPage.tsx` và bổ sung test trong `ui/src/pages/Vision/ReviewRowNames.test.tsx`.
4. Chạy toàn bộ kiểm chứng (`unittest`, `tsc --noEmit`, `vitest`, `check_generated.py`), cập nhật trạng thái `✅ Done` và tạo PR.

## Hồ sơ liên quan

- [ISSUE-018](../ISSUE-018-ke-hoach-theo-thanh-vien/issue.md) — Kế hoạch theo thành viên (dòng 33)
- [AI_CONVENTIONS](../../../../standards/AI_CONVENTIONS.md) — Quy ước ANPR & AI Console
