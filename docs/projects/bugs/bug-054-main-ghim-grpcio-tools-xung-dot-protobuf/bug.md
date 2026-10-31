# 🐛 bug-054: `main` ghim `grpcio-tools==1.84.1` cùng `protobuf==5.29.5`, pip không cài được nên image build hỏng

> **Đích:** `docs/projects/bugs/bug-054-main-ghim-grpcio-tools-xung-dot-protobuf/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New |
| **Người nhận** |  |
| **Hạn** |  |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** |  |
| **Ngày báo** | 2026-10-31 |
| **Người báo** | Claude Code, lúc kiểm bug-053 (2026-10-31) |
| **Môi trường** | `main` `82af07f` |

## Hành vi thực tế

Trên `main`, `requirements-service.txt` và `requirements.txt` ghim `grpcio==1.84.1`, `grpcio-tools==1.84.1` và `protobuf==5.29.5`. Bản `grpcio-tools 1.84.1` khai `Requires-Dist: protobuf<8.0.0,>=7.35.1`, nên pip dừng với `ResolutionImpossible`. Bước `RUN pip install -r requirements-service.txt` của `Dockerfile` vì thế không qua được.

`develop` (`fa3ea51`) vẫn ghim `1.71.0` cho cả ba gói, khớp nhau. Lệch này do Dependabot nâng thẳng trên `main`; comment ngay trên dòng ghim đã cảnh báo rằng grpcio-tools mới sinh code protobuf 7.

## Hành vi mong đợi

`main` cài được dependency. Hoặc giữ `grpcio`/`grpcio-tools` ở dòng tương thích protobuf 5, hoặc nâng đồng bộ cả protobuf runtime rồi sinh lại stub và chạy test. Dependabot không được tách ba gói này.

## Tái hiện

1. `pip download --no-deps --only-binary=:all: --python-version 3.12 --platform manylinux_2_17_x86_64 grpcio-tools==1.84.1`
2. Đọc `METADATA` trong wheel: `Requires-Dist: protobuf<8.0.0,>=7.35.1`.
3. `pip download grpcio-tools==1.84.1 protobuf==5.29.5 …` → `ResolutionImpossible`.

## Bằng chứng

- Output pip (2026-10-31): `ERROR: Cannot install grpcio-tools==1.84.1 and protobuf==5.29.5 because these package versions have conflicting dependencies.`
- `git show origin/develop:requirements-service.txt` → `grpcio==1.71.0`, `grpcio-tools==1.71.0`, `protobuf==5.29.5`.

## Sửa / kiểm chứng

<Điền sau khi sửa. Gợi ý: đưa `develop` lên `main` qua PR, thêm nhóm Dependabot gom `grpcio*` + `protobuf`, hoặc `ignore` major/minor của grpcio-tools cho tới khi nâng protobuf 7.>
