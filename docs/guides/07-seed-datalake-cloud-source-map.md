# 📘 [Guide] Seed → PostgreSQL → Data lake → Cloud: source map và runbook

> **Mục tiêu:** đọc tài liệu là lần được ngay tới file code, biết phần nào đã chạy,
> phần nào mới là scaffold và thứ tự triển khai cloud an toàn.

## 📌 Trạng thái thật ngày 2026-09-21

| Khâu | Trạng thái | Kết luận |
|---|---|---|
| Seed PostgreSQL bằng NestJS/TypeORM | ✅ Có code | Có 5 seeder chạy theo thứ tự và CLI chọn từng seeder |
| Export `parking_sessions` tăng dần | ✅ Có code + test | Ghi JSONL bất biến, manifest SHA-256 và watermark local |
| Đọc raw thành occupancy 30 phút | ✅ Có code + test | Dedup theo `session_id/updated_at`, tính overlap theo khoảng nửa mở |
| Snapshot/features/baseline/ridge offline | ✅ Có code + test | Chưa được phép phục vụ production vì chưa có dữ liệu lịch sử đủ gate |
| Backend upload media lên S3-compatible | ✅ Có adapter | PUT/delete/presigned PUT; đang chọn bằng `STORAGE_DRIVER` |
| AI tải model bằng signed URL | ✅ Có downloader | Download-only, có giới hạn bytes và kiểm SHA-256 |
| Đồng bộ data lake local lên S3/R2 | ❌ Chưa có | `AI_DATALAKE_S3_BUCKET` hiện chỉ là config, chưa có uploader |
| Materialize dataset/publish model cloud | 🟡 Scaffold | CLI chỉ in trạng thái kế hoạch, chưa truyền bytes |

[GOTCHA] `S3Adapter` của backend, `SignedUrlObjectStore` của AI và data lake là
ba vai trò khác nhau. Có hai adapter đầu không có nghĩa data lake đã tự lên cloud.

## 🗺️ Luồng đang có và biên cloud còn thiếu

```mermaid
flowchart LR
    SEED[NestJS TypeORM seed] --> PG[(PostgreSQL nghiệp vụ)]
    PG --> EX[ParkingSessionExporter]
    EX --> RAW[Local raw JSONL + manifest]
    EX --> WM[Local watermark]
    RAW --> READER[OccupancyHistoryReader]
    READER --> SNAP[Snapshot bất biến]
    SNAP --> FEAT[Feature splits theo thời gian]
    FEAT --> BASE[Baseline/backtest]
    FEAT --> MODEL[Ridge candidate offline]

    RAW -. chưa có publisher .-> OBJ[(S3 / R2 / S3-compatible)]
    SNAP -. chưa có publisher .-> OBJ
    MODEL -. publish_model hiện là scaffold .-> OBJ

    MEDIA[Backend StorageProvider] --> S3A[S3Adapter]
    S3A --> OBJ
    OBJ --> SIGNED[Signed URL]
    SIGNED --> DL[AI model artifact downloader]
```

## 🔎 Bản đồ code — bắt đầu đọc từ đâu

### 1. Seed dữ liệu nghiệp vụ

| File/hàm | Vai trò |
|---|---|
| [run-seed.ts](../../../backend/src/infrastructures/Database/TypeORM/run-seed.ts), `main()` | Parse `--sync`, `--drop`, `--only`; kết nối DB rồi gọi runner |
| [seed/index.ts](../../../backend/src/infrastructures/Database/TypeORM/seed/index.ts), `SeedRunner` | Registry và thứ tự 5 seeder; lọc bằng `DB_SEED_INCLUDE`/`--only` |
| [database.config.ts](../../../backend/src/configs/database.config.ts), `seedConfig()` | Nguồn duy nhất của số lượng seed từ biến `DB_SEED_*` |
| [05-demo-data.seeder.ts](../../../backend/src/infrastructures/Database/TypeORM/seed/seeders/demo/05-demo-data.seeder.ts) | Tạo user/xe/demo session hiện tại, reservation, subscription, dispute |

Tên seeder dùng với `--only`: `role`, `vehicle-type`, `parking-area`,
`parking-lot-slot`, `demo-data`.

[GOTCHA] `demo-data` hiện **xoá toàn bộ** `parking_session_histories`,
`parking_sessions`, `reservations` và `slot_subscriptions` trước khi dựng lại dữ
liệu demo. Chỉ chạy trên local/dev database có chủ đích; không chạy vào DB cần
giữ lịch sử.

[GOTCHA] Demo seeder chủ yếu tạo session `active` quanh thời điểm hiện tại. Nó
đủ để thử schema/export, nhưng không tạo lịch sử 30–365 ngày đủ để đánh giá
forecast. `seed_datalake_logs.py` tạo dữ liệu random ở tầng `silver` với contract
khác reader production; chỉ dùng demo, không dùng làm bằng chứng model.

### 2. PostgreSQL → data lake local

| File/hàm | Vai trò |
|---|---|
| [export_parking_sessions.py](../../app/script/export_parking_sessions.py), `main()` | CLI `--status`, `--since`, `--until`, `--output` |
| [session_exporter.py](../../app/infra/datalake/session_exporter.py), `ParkingSessionExporter.export()` | Query incremental `(after, until]`, stream batch, ghi JSONL/manifest/watermark |
| `ParkingSessionExporter._query()` | Chọn đúng cột session/capacity; loại user, vehicle, plate và media |
| [datalake_config.py](../../app/config/datalake_config.py), `DatalakeConfig` | Local path, batch size, slot minutes; `s3_bucket` chưa được dùng để upload |
| [occupancy_reader.py](../../app/infra/datalake/occupancy_reader.py), `OccupancyHistoryReader` | Đọc raw, lấy version session mới nhất, tổng hợp occupancy 30 phút |

Layout được code tạo:

```text
ai/data/datalake/
├── raw/parking_sessions/export_date=YYYY-MM-DD/
│   ├── <run-id>.jsonl
│   └── <run-id>.manifest.json
└── _state/parking_sessions.json
```

Manifest chứa schema version, cửa sổ watermark, row count, SHA-256 và
`contains_pii=false`. Watermark chỉ được thay sau khi data file và manifest local
đã ghi thành công.

### 3. Data lake → snapshot → model candidate

| File/hàm | Vai trò |
|---|---|
| [readiness.py](../../training/readiness.py), `inspect_forecast()` | Gate read-only: raw manifest/hash, capacity và độ phủ lịch sử |
| [snapshot.py](../../training/forecast/snapshot.py), `main()` | Đóng băng occupancy đều theo một `as_of` xác định |
| [build_features.py](../../training/forecast/build_features.py), `main()` | Tạo lag/rolling/calendar features và chia train/validation/test theo thời gian |
| [backtest.py](../../training/forecast/backtest.py), `main()` | Đo persistence và weekly seasonal-naive |
| [train.py](../../training/forecast/train.py), `main()` | Train ridge offline; artifact luôn là candidate, không tự deploy |

### 4. Storage/cloud hiện có

| File/hàm | Có gì và chưa có gì |
|---|---|
| [storage.provider.ts](../../../backend/src/infrastructures/Storage/storage.provider.ts), `StorageProvider` | API upload chung, upload raw, key/prefix, presigned PUT |
| [s3.adapter.ts](../../../backend/src/infrastructures/Storage/adapters/s3.adapter.ts), `S3Adapter` | AWS S3 hoặc endpoint S3-compatible; chưa phải data-lake sync job |
| [storage.config.ts](../../../backend/src/configs/storage.config.ts) | Map `STORAGE_DRIVER`, bucket, endpoint, credential |
| [object_store.py](../../app/infra/storage/object_store.py), `SignedUrlObjectStore` | AI tải object qua signed HTTPS URL và kiểm hash; không có PUT/list/delete |
| [artifact_store.py](../../app/infra/model_registry/artifact_store.py) | Dùng downloader trên để materialize model vào cache |
| [materialize_dataset.py](../../training/materialize_dataset.py) | Scaffold trạng thái, chưa download snapshot thật |
| [publish_model.py](../../training/publish_model.py) | Scaffold trạng thái, chưa upload candidate thật |

## 🪜 Runbook local — seed rồi export đúng contract

### Bước 1: cấu hình và seed backend

Sao chép `backend/.env.example` thành file `.env` local và kiểm DB. Không commit
password/access key. Trên PowerShell:

```powershell
cd backend
npm run infra:status
npm run migration:run

# Chạy đủ 5 seeder theo registry.
npm run db:seed

# Hoặc chọn rõ từng seeder. Các dependency phải tồn tại trước demo-data.
npm run db:seed -- --only role,vehicle-type,parking-area,parking-lot-slot,demo-data
```

Chỉ dùng `npm run db:seed:sync` khi local database chưa có schema và bạn đã xác
nhận `DB_SCHEMA_MODE`. `db:seed:drop` là thao tác xoá/recreate schema, không nằm
trong runbook bình thường.

### Bước 2: trỏ AI exporter vào đúng PostgreSQL

`ParkingSessionExporter` đang dùng `AI_DATABASE_URL`:

```powershell
cd ..\ai
$env:AI_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/iplms_db"

# Chỉ in config, không kết nối DB và không ghi file.
.\.venv\Scripts\python.exe -m app.script.export_parking_sessions --status
```

Nếu backend DB chạy ở cổng/host khác, sửa URL local tương ứng. Không đưa URL có
password thật vào tài liệu, commit hoặc log CI.

### Bước 3: export incremental

```powershell
# Lần đầu: mặc định đọc từ epoch đến thời điểm chạy.
.\.venv\Scripts\python.exe -m app.script.export_parking_sessions

# Cửa sổ có chủ đích để debug/replay sang một workspace riêng.
.\.venv\Scripts\python.exe -m app.script.export_parking_sessions `
  --since "2026-09-01T00:00:00Z" `
  --until "2026-09-21T00:00:00Z" `
  --output data\datalake-debug
```

Kiểm file và manifest:

```powershell
Get-ChildItem data\datalake\raw\parking_sessions -Recurse -File
Get-Content data\datalake\_state\parking_sessions.json
.\.venv\Scripts\python.exe -m training.readiness --scope forecast --json
```

Không sửa tay watermark để “cho chạy qua”. Nếu export lỗi DB, exporter xoá file
`.part` và không advance watermark.

### Bước 4: snapshot và đánh giá khi readiness đủ

```powershell
.\.venv\Scripts\python.exe -m training.forecast.snapshot `
  --data-lake data\datalake `
  --days 180 `
  --as-of "2026-09-21T00:00:00Z"

# Thay đường dẫn manifest bằng output thật của lệnh snapshot.
.\.venv\Scripts\python.exe -m training.forecast.backtest `
  --snapshot-manifest data\datalake\curated\occupancy\<snapshot>.manifest.json `
  --report data\datalake\reports\forecast-baseline.json

.\.venv\Scripts\python.exe -m training.forecast.build_features `
  --snapshot-manifest data\datalake\curated\occupancy\<snapshot>.manifest.json

# Thay bằng feature manifest vừa sinh.
.\.venv\Scripts\python.exe -m training.forecast.train `
  --feature-manifest data\datalake\curated\forecast_features\<features>.manifest.json
```

Nếu readiness đỏ vì thiếu ngày lịch sử/capacity, dừng ở đây. Hạ gate hoặc dùng
random seed có thể phục vụ smoke test, nhưng không biến metric thành bằng chứng
production.

### Bước 5: test code path

```powershell
.\.venv\Scripts\python.exe -m unittest `
  test.test_datalake `
  test.test_training_readiness `
  test.test_forecast_training -v
```

## ☁️ Chặng cloud kế tiếp — triển khai gì, không “copy folder bằng tay”

### Ranh giới adapter đề xuất

Chưa nên gọi trực tiếp AWS SDK từ exporter. Giữ exporter tạo partition local
bất biến, rồi thêm một sync/publisher idempotent:

```text
ai/app/infra/datalake/object_publisher.py       # interface put/head + receipt
ai/app/infra/datalake/s3_object_publisher.py    # AWS S3/R2/S3-compatible adapter
ai/app/script/sync_datalake_objects.py          # scan manifest chưa sync, upload/retry
ai/data/datalake/_state/remote-sync.json        # trạng thái sync riêng watermark DB
```

`AI_DATALAKE_S3_BUCKET` chỉ nên được coi là có tác dụng sau khi các file trên có
implementation và test. Không dùng watermark export DB làm trạng thái upload
cloud; export có thể thành công trong khi mạng/S3 thất bại và cần retry sau.

### Object key ổn định

```text
datalake/raw/parking_sessions/export_date=YYYY-MM-DD/<run-id>.jsonl
datalake/raw/parking_sessions/export_date=YYYY-MM-DD/<run-id>.manifest.json
datalake/curated/occupancy/<snapshot-id>/...
datalake/features/forecast/<artifact-id>/...
models/forecast/candidates/<candidate-id>/manifest.json
```

Thứ tự publish một partition:

1. Upload data object bằng key bất biến; không overwrite.
2. `HEAD`/receipt và kiểm byte size + checksum metadata.
3. Upload manifest sau khi data object đã xác minh.
4. Ghi trạng thái remote-sync/catalog cuối cùng.
5. Retry cùng key phải idempotent; hash khác cùng key là lỗi, không ghi đè.

### Cấu hình provider

- AWS S3: để `S3_ENDPOINT` rỗng ở backend; dùng region/bucket đúng account.
- R2 hoặc S3-compatible: truyền endpoint riêng qua adapter, không rải `if AWS`
  trong code nghiệp vụ.
- Bucket/prefix raw, curated và model cần quyền/lifecycle khác nhau dù có thể nằm
  chung một provider.
- Runtime cloud ưu tiên role/workload identity; credential local chỉ nằm trong
  `.env` gitignored. Không commit access key hoặc signed URL.
- Bucket private; DB/catalog giữ provider + bucket + key + version/hash. Signed
  URL chỉ để truy cập tạm thời, không làm ID bền.

## ✅ Definition of done cho lượt nối cloud

- [ ] Upload data + manifest, tải lại và kiểm SHA-256 khớp.
- [ ] Tắt mạng giữa chừng rồi retry không tạo object logic trùng.
- [ ] Export watermark và remote-sync state độc lập.
- [ ] Không có plate/user/vehicle/media URL trong forecast export.
- [ ] Role AI chỉ đọc prefix input và ghi prefix artifact được cấp.
- [ ] Lifecycle không xoá object còn được dataset/model manifest tham chiếu.
- [ ] `materialize_dataset.py` và `publish_model.py` có implementation thật,
      test idempotency và không tự đổi alias model accepted.
- [ ] Báo cáo local và cloud dùng cùng manifest/hash, không “train từ folder mới nhất”.

## 🔗 Liên quan

- [Forecast từ PostgreSQL đến model](./04-forecast-training-strategy.md)
- [Worker, storage và vòng đời dữ liệu](./05-ai-workers-storage-and-training-lifecycle.md)
- [Google Colab training](./06-google-colab-training-runbook.md)
- [PROB-039: Forecast từ session đến model thật](../../../docs/problems/09-2026/PROB-039-forecast-tu-session-den-model-that.md)
- [Dual-track AWS và VPS/K3s](../../../docs/problems/09-2026/PROB-037-dual-track-deployment-aws-vs-vps-k3s.md)
