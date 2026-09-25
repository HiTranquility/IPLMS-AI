# core/dataset — Chọn ảnh để người review + khoá snapshot dữ liệu train

> Trạng thái (2026-09-25): **logic có, chưa nối vào luồng thật.** `CurationService` và `SnapshotService` chỉ được gọi từ test (`test/test_dataset_curation.py`). Không có hàng đợi review, không có nơi lưu ảnh ứng viên, `training/materialize_dataset.py` / `validate_dataset.py` còn là mốc CLI chưa làm.

## Nguyên tắc

**Dự đoán của máy KHÔNG bao giờ tự thành nhãn (ground truth).** Máy chỉ *đề xuất* ảnh đáng xem; người review gán nhãn đúng; chỉ mẫu đã review mới vào snapshot train/val/test-golden. Biển số là dữ liệu cá nhân — ảnh không vào git (`data/golden/` chỉ giữ nhãn + số đo).

## Luồng dự kiến (một ảnh sau khi ANPR xong)

```text
curation_service.evaluate(image_bytes, model_confidence, human_corrected, random_audit_sample)
  ├─ engines/image_quality.inspect_image_quality     đo kỹ thuật
  │     ≥160×120 px · độ sáng 25–235 · độ nét (phương sai Laplacian) ≥ 20
  │     → acceptable + lý do: too_small / too_dark / too_bright / too_blurry
  └─ engines/sample_selector.select_sample           có đáng đưa người xem?
        chọn nếu CÓ ÍT NHẤT MỘT lý do:
          human_correction   nhân viên đã sửa biển máy đọc (mẫu quý nhất)
          low_confidence     điểm ANPR < 0.75
          random_audit       ảnh đạt chất lượng + được bốc ngẫu nhiên để kiểm (tránh chỉ học ca khó)
          quality_edge_case  ảnh không đạt chất lượng (tối, mờ, nhỏ) — ca biên
        ảnh không decode được → không chọn ("invalid_image")
→ (chưa có) hàng đợi review → người gán nhãn
→ services/snapshot_service.build_lock(dataset_id, samples)
        mẫu đã review → manifest ổn định (sắp theo id, sha256), split ∈ train | val | test-golden
```

## Trả lời nhanh: "bao nhiêu % thì ảnh được chuyển đi?"

- **< 75%** điểm tin cậy ANPR → đề xuất review (`low_confidence_threshold=0.75`, `sample_selector.py`).
- **≥ 75%** → không chọn, **trừ** khi nhân viên đã sửa biển, hoặc ảnh được bốc kiểm ngẫu nhiên, hoặc ảnh kém chất lượng.
- Tỉ lệ bốc kiểm ngẫu nhiên **chưa được định nghĩa** — người gọi truyền `random_audit_sample=True/False`, chưa có ai quyết định bao nhiêu %.
- Ví dụ thật: ảnh demo `59C-888.66` có điểm 0.6685 → sẽ được đề xuất review.

## Việc còn thiếu để chạy thật

1. Backend gọi curation sau mỗi lượt check-in (hoặc `ai/` tự gọi trong `anpr_service`) và lưu ảnh ứng viên vào kho riêng (không lẫn folder `Sessions` bằng chứng).
2. Hàng đợi + màn review gán nhãn (ai review? cần quyết định).
3. Chốt tỉ lệ bốc kiểm ngẫu nhiên và thời hạn lưu ảnh (PII).
4. Làm thật `materialize_dataset` / `validate_dataset`.

## File

| File | Việc |
|---|---|
| `engines/image_quality.py` | Kích thước, độ sáng, độ nét — thuần OpenCV |
| `engines/sample_selector.py` | Luật chọn + lý do |
| `services/curation_service.py` | Ghép hai bước trên cho một ảnh |
| `services/snapshot_service.py` | Khoá manifest snapshot (chống trùng id, split hợp lệ, sha256) |
| `dtos/sample_dto.py` | `ImageQualityReport`, `CurationResult`, `SnapshotSample` |
