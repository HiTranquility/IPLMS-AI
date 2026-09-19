# `ml/` — workspace offline cho Machine Learning

`ml/` không phải database nghiệp vụ và cũng không phải datalake production. Đây
là nơi các script trong [`training/`](../training/README.md) vật hoá một snapshot
dữ liệu để train/evaluate và ghi artifact sinh ra trong quá trình thử nghiệm.

```text
Nguồn thật có kiểm soát                    Workspace local                 Kết quả
Object storage + catalog + nhãn duyệt ──► ml/dataset/<task>/ ──train──► ml/checkpoint/<run>/
                                                │                              │
                                                └──evaluate─────────────────────┘
```

## Vì sao có `ml/dataset/`?

Model không train trực tiếp trên bảng session hoặc bucket đang thay đổi từng
phút. Mỗi lần train cần một **snapshot đứng yên**: đúng ảnh nào, nhãn gì, thuộc
train/validation/test và được chia theo quy tắc nào. `ml/dataset/` là bản local
được materialize từ snapshot đó để PyTorch đọc nhanh.

Tên thư mục dùng số ít `dataset/` vì nó là loại tài nguyên trong cây `ml/`; bên
trong có thể chứa nhiều dataset theo từng task. Không tạo thêm `datasets/` song
song vì hai tên sẽ trở thành hai nguồn sự thật.

## Bản đồ và ranh giới

| Nơi | Chứa gì | Có vào Git? |
|---|---|---|
| `data/golden/plates/` | Bộ vàng **đo ANPR**, không dùng train | Nhãn/report có; ảnh không |
| `data/knowledge/` | Seed/evaluation cho RAG | File nhỏ đã duyệt có thể có |
| `ml/dataset/<task>/` | Snapshot train/val/test đã vật hoá | README + lock đã làm sạch; ảnh không |
| `ml/checkpoint/<run>/` | Checkpoint, metric, dataset/config fingerprint | Metric/lock có; weight lớn không |
| `models/` | Kiến trúc model và artifact được runtime nạp theo policy repo | Tuỳ artifact; `best.pt` hiện là ngoại lệ |
| Object storage private | Raw image, curated image, Parquet, private manifest, checkpoint lớn | Không nằm trong Git |

`raw/` trong một dataset local chỉ là cache đầu vào của tác vụ chuẩn bị dữ liệu.
Nguồn sự thật vẫn là object storage + catalog. Xoá workspace phải có thể dựng
lại từ snapshot private; không được xem một folder ảnh trên laptop là datalake.

## Mỗi task có dataset riêng

Không dùng chung một layout/nhãn cho mọi bài toán:

| Task | Thư mục khi thật sự triển khai | Nhãn cần có |
|---|---|---|
| Phân loại xe | `dataset/vehicle-cls/` — hiện có khung | `motorbike/car/truck/bicycle` |
| Detect biển | `dataset/plate-detector/` — tạo khi bắt đầu phase | Bounding box + ảnh không có biển được duyệt |
| OCR biển | `dataset/plate-ocr/` — tạo khi bắt đầu phase | Crop biển + chuỗi chuẩn + layout khi cần |
| Vehicle ReID | `dataset/vehicle-reid/` — tạo khi bắt đầu phase | Identity hoặc cặp cùng/khác xe |

Forecast dùng snapshot chuỗi thời gian/Parquet; RAG dùng corpus và bộ câu hỏi
đánh giá. Không nhét hai loại này vào ImageFolder chỉ để mọi thứ cùng tên
“dataset”. Xem [worker, storage và vòng đời dữ liệu](../docs/guides/05-ai-workers-storage-and-training-lifecycle.md).

## Tối thiểu cần có trước một lần train thật

1. Private manifest ánh xạ object key/version tới nhãn đã duyệt.
2. `dataset.lock.json` đã làm sạch: hash, label, split và group hash; không chứa
   signed URL, biển số, tên người hay secret.
3. Split theo vehicle/session/burst để ảnh gần trùng không lọt sang tập khác.
4. `label_schema_version`, `dataset_id`, `source_cutoff`, seed và quy tắc split.
5. Preprocessing/class order khớp runtime và được ghi cùng checkpoint.
6. Script validate không có duplicate hash, nhãn lạ, ảnh hỏng hay group leakage.
7. Script evaluate riêng cho test-golden; train script không được đọc tập này.

Ba script còn thiếu nhưng đáng làm trước khi train production:

```text
training/materialize_dataset.py       private manifest → workspace local
training/validate_dataset.py          schema/hash/class balance/group leakage
training/eval_vehicle_classifier.py   checkpoint → metric + confusion matrix
```

Chỉ tạo chúng khi bắt đầu phase tương ứng. File rỗng không làm pipeline hoàn
chỉnh hơn.

## Colab nằm ở đâu trong luồng này?

Colab là **máy chạy một training run**, không phải nơi giữ dữ liệu hoặc registry
model. Notebook nên gọi lại CLI trong `training/` thay vì chép logic train vào
các cell. Luồng đầy đủ:

```text
Git commit + dataset snapshot → Colab GPU → checkpoint + metrics
                                      │
                                      └─► object storage/model catalog
                                                     │
                                              approve + deploy
```

Dataset được tải một lần về disk tạm `/content` rồi train tại đó; không đọc hàng
nghìn ảnh trực tiếp từ Google Drive trong mỗi epoch. Checkpoint resume được sync
định kỳ ra kho bền vì runtime Colab là tạm thời. Kết quả cuối phải upload cùng
dataset hash, class mapping, preprocessing và source commit; “Download model” về
laptop chỉ là bản sao tiện dụng, không phải nguồn sự thật.

Runbook: [Google Colab training](../docs/guides/06-google-colab-training-runbook.md).

## Dọn dữ liệu mà không phá khả năng tái lập

- Có thể xoá ảnh materialize và checkpoint local sau khi artifact đã upload và
  kiểm hash.
- Không xoá object mà dataset/model accepted còn tham chiếu nếu chưa có policy
  xử lý lineage.
- `dataset.lock.json` đi cùng checkpoint. Chỉ lưu lock ở folder dataset hiện tại
  là chưa đủ vì snapshot đó sẽ thay đổi ở lần train sau.
- Dataset mới tạo `dataset_id` mới; không sửa âm thầm snapshot cũ để làm metric
  đẹp hơn.

Quyết định nền: [ADR-0003](../../docs/projects/adrs/0003-duong-du-lieu-vision-tu-phien-do-toi-checkpoint.md).
