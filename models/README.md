# `models/` — Kiến trúc CNN (Block ↔ Backbone)

Giữ nguyên layout của code gốc: mỗi "model" (M1/M2) có `backbones.py` (định nghĩa các **Block**) + `nets.py` (định nghĩa **Net/Backbone** ghép block) + `externals/` (block dùng chung như SE). Đã **bỏ tách theo tên sinh viên**; `Phat` là bản canonical.

| Model | Net | Block | Đặc điểm |
|---|---|---|---|
| [`m1/`](m1/) | `NetV1` | BlockV1/V2/V3 (residual thuần) | Midterm — 3 stage, 7 block, không SE, không dropout |
| [`m2/`](m2/) | `NetV2` | BlockV1/V2/V3 (+ SE) | Final — 4 stage, 8 block, SE mọi stage, dropout 0.2, bottleneck |

Import trong service/scripts:
```python
from models.m1.nets import NetV1
from models.m2.nets import NetV2
```
(Chạy từ thư mục `ai/` hoặc để `ai/` trên `PYTHONPATH`; các script `training/` đã tự thêm `ai/` vào `sys.path`.)
