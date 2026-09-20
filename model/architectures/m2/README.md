# `model/architectures/m2` — NetV2 (Final)

## Giải quyết gì
Cải tiến từ NetV1: thêm **SE attention** (nhấn kênh đặc trưng), khối **bottleneck** sâu hơn, **dropout** chống overfit → độ chính xác cao hơn trên CIFAR-10/100.

## Block dùng (`backbones.py`, đều kèm SE + residual)
- **BlockV1** — 2× Conv3x3 + SE + residual (đặc trưng cục bộ).
- **BlockV2** — depthwise-separable (conv rẻ) + SE + residual (pattern trung cấp, hiệu quả).
- **BlockV3** — bottleneck 1x1→3x3→1x1 + SE + residual (semantic sâu).
- **SE** (`externals/se_attention.py`) — squeeze (global avg pool) → excitation (MLP + sigmoid) → nhân trọng số kênh.

## So với M1
SE ở **mọi** stage (M1 không có), sâu hơn (8 block/4 stage vs 7/3), `bias=False` toàn bộ (BN lo bias), dropout 0.2 trước FC.

## Backbone (`nets.py` → `NetV2`)
`stem(s=2)` → stage1..4 → GAP → Dropout → FC. Input 32×32 → 1×1, 512 kênh → `n_class`.

## Chạy / train
```python
from model.architectures.m2.nets import NetV2
m = NetV2(n_class=10)
```
```bash
python training/train_cifar.py -d cifar10 --download -e 200
python training/train_cifar.py -d cifar100 --download -e 200
```
