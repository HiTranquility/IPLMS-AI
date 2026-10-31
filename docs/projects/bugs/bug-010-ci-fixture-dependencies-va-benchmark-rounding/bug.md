# 🐛 bug-010: CI unit thiếu runtime dependencies và benchmark fixture bị làm tròn về 0

> **Đích:** `docs/projects/bugs/bug-010-ci-fixture-dependencies-va-benchmark-rounding/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Ngày / Người báo** | 2026-10-16 / Codex |
| **Trạng thái** | ✅ Fixed — Đã bổ sung runtime dependencies vào CI (.github/workflows/ci.yml) và chuẩn hoá benchmark. |
| **Ngày đóng** | 2026-10-31 |
| **Nguồn** | IPLMS ISSUE-124; checkPython củaPR17 |

Check Python tự chạy của PR 17 báo thiếu `fastapi`/`pyarrow` (runtime đã có trong requirements nhưng CI cài thiếu), cùng một benchmark assertion thất bại. Tỷ số dương của detector giả lập bị làm tròn hai chữ số thành 0.0; đây là lỗi độ chính xác của báo cáo, chưa chứng minh hiệu năng model thật.

Đã bổ sung dependency runtime vào CI, giữ giá trị mean và ratio đầy đủ trước khi format báo cáo. Unit test dùng ảnh synthetic và mock cả initializer PyTorch lẫn ONNX, không đọc ảnh hay checkpoint thật. Các test Lakehouse dùng dữ liệu thật cần opt-in `AI_RUN_REAL_LAKEHOUSE_TESTS=1`; test pipeline với thư mục tạm vẫn chạy mặc định.

Kiểm chứng local: nhóm benchmark/Parquet/Lakehouse có 20 PASS, 7 SKIP do cần dữ liệu thật. Sau khi bổ sung mock ONNX, ba test bị ảnh hưởng (report, precision và pipeline cô lập) PASS. Reviewer độc lập kiểm diff cuối, không còn finding trong phạm vi này. Chưa xác nhận check PR chạy lại; SKIP không phải PASS.
