# `model/` — vòng đời model trong workspace

Đây là root duy nhất cho phần model: mã kiến trúc, dataset local, checkpoint và
artifact bootstrap. [WORKSPACE.md](WORKSPACE.md) giải thích ranh giới với object
storage, datalake và Git.

| Thư mục | Vai trò | Nguồn sự thật |
|---|---|---|
| `architectures/` | Mã Python của NetV1/NetV2 | Git |
| `artifacts/bootstrap/` | Weight mẫu cần để service chạy sau khi clone | Git, chỉ ngoại lệ nhỏ đã duyệt |
| `dataset/` | Snapshot local đã materialize để train/evaluate | Object storage + catalog |
| `checkpoint/` | Checkpoint và metric trong lúc train | Object storage sau khi publish |
| `runs/` | Output tạm theo từng training run | Model catalog/artifact storage |

Model candidate/accepted có version nằm trong object storage private và được
cache ở `var/model-cache/`; không chép weight production vào Git.

## Prefix chuẩn trong object storage

Một bucket private `iplms-ai` là đủ cho quy mô hiện tại. Prefix tách quyền,
lifecycle và loại artifact; RabbitMQ chỉ mang key/version/hash, không mang bytes.

```text
iplms-ai/
├── raw/vision/YYYY/MM/DD/<capture-id>/original.jpg
├── derived/vision/<capture-id>/<pipeline-version>/plate-crop.jpg
├── datasets/vehicle-cls/<dataset-id>/
│   ├── manifest.private.json
│   ├── dataset.lock.json
│   └── shards/
├── runs/vehicle-cls/<run-id>/resume/
└── models/vehicle-cls/<model-version>/
    ├── model.pth
    ├── model-manifest.json
    ├── dataset.lock.json
    ├── metrics.json
    └── checksums.sha256
```

`raw/` và manifest private chứa dữ liệu nhạy cảm. `datasets/`, `runs/` và
`models/` ở đây là prefix bên trong bucket, nên không chịu quy tắc đặt tên folder
root của source tree.

Mỗi kiến trúc (M1/M2) có `backbones.py` (định nghĩa các **Block**) + `nets.py` (định nghĩa **Net/Backbone** ghép block) + `externals/` (block dùng chung như SE).

| Model | Net | Block | Đặc điểm |
|---|---|---|---|
| [`architectures/m1/`](architectures/m1/) | `NetV1` | BlockV1/V2/V3 (residual thuần) | Midterm — 3 stage, 7 block, không SE, không dropout |
| [`architectures/m2/`](architectures/m2/) | `NetV2` | BlockV1/V2/V3 (+ SE) | Final — 4 stage, 8 block, SE mọi stage, dropout 0.2, bottleneck |

Import trong service/scripts:
```python
from model.architectures.m1.nets import NetV1
from model.architectures.m2.nets import NetV2
```
(Chạy từ thư mục `ai/` hoặc để `ai/` trên `PYTHONPATH`; các script `training/` đã tự thêm `ai/` vào `sys.path`.)
