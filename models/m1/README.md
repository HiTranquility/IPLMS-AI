# `models/m1` — NetV1 (Midterm)

## Giải quyết gì
Bộ phân loại ảnh CNN "chắc tay" đầu tiên: residual skip connection trên mọi block để train sâu ổn định (mục tiêu acc 70–80%+ trên Animal-10 / CIFAR).

## Block dùng (`backbones.py`)
- **BlockV1** — 1× Conv3x3 + BN + ReLU + residual (đặc trưng cơ bản: cạnh, texture).
- **BlockV2** — 2× Conv3x3 + residual (pattern trung cấp; ReLU **sau** phép cộng).
- **BlockV3** — bottleneck 1x1→3x3→1x1 + residual (semantic sâu, nén channel ½).

## Backbone (`nets.py` → `NetV1`)
`stem(Conv3x3 s=2)` → Stage1 (BlockV1×2) → Stage2 (BlockV2×2) → Stage3 (BlockV3×3) → GAP → FC. Input 32×32 → 1×1, 512 kênh → `n_class`.

## Chạy / train
```python
from models.m1.nets import NetV1
m = NetV1(n_class=10)
```
```bash
python training/train_imagefolder.py --data ./ml/dataset/Animal-10 --net NetV1 --img-size 32 --epochs 100
python training/test_animal10.py     # eval trên test set
```
