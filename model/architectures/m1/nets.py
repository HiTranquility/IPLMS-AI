from model.architectures.m1.backbones import *


class NetV1(nn.Module):
    """
    M1 Network (NetV1) — Midterm.

    Residual skip connections trên mọi block:
    ❌ Cũ:  Plain blocks, không skip → acc ~59% rồi bão hòa
    ✅ Mới: Residual skip connections → dự kiến acc 70-80%+

    ┌────────────────────────────┬──────────────────┬──────────────────┐
    │ Kỹ thuật                   │ Cũ               │ Mới              │
    ├────────────────────────────┼──────────────────┼──────────────────┤
    │ Residual (skip connection) │ ❌ Không          │ ✅ Tất cả block  │
    └────────────────────────────┴──────────────────┴──────────────────┘

    Flow tính kích thước (input 32×32):
    ┌─────────┬──────────────┬────────┬────────┬──────────┬──────────┐
    │ Layer   │ Block type   │ Stride │ W×H in │ W×H out  │ Channels │
    ├─────────┼──────────────┼────────┼────────┼──────────┼──────────┤
    │ stem    │ Conv3x3      │   2    │ 32×32  │  16×16   │ 3→32     │
    │ b1      │ BlockV1 (1c) │   1    │ 16×16  │  16×16   │ 32→64    │
    │ b2      │ BlockV1 (1c) │   2    │ 16×16  │   8×8    │ 64→64    │
    │ b3      │ BlockV2 (2c) │   2    │  8×8   │   4×4    │ 64→128   │
    │ b4      │ BlockV2 (2c) │   1    │  4×4   │   4×4    │ 128→128  │
    │ b5      │ BlockV3 (3c) │   2    │  4×4   │   2×2    │ 128→256  │
    │ b6      │ BlockV3 (3c) │   1    │  2×2   │   2×2    │ 256→256  │
    │ b7      │ BlockV3 (3c) │   2    │  2×2   │   1×1    │ 256→512  │
    │ pool    │ AvgPool      │   -    │  1×1   │   1×1    │ 512      │
    │ fc      │ Linear       │   -    │   -    │    -     │ 512→n    │
    └─────────┴──────────────┴────────┴────────┴──────────┴──────────┘

    Sơ đồ dữ liệu chảy qua network:

    Input (3, 32, 32)
      │
      ▼
    ┌──────────────────┐
    │   STEM           │  Conv3x3(s=2) → BN → ReLU
    │   3→32, 32→16    │
    └────────┬─────────┘
             │ (32, 16, 16)
             ▼
    ┌──────────────────┐
    │  STAGE 1: Detail │  BlockV1 × 2 (edge, texture)
    │  b1: 32→64  s=1  │──→ [Conv→BN→ReLU] + skip
    │  b2: 64→64  s=2  │──→ [Conv→BN→ReLU] + skip
    └────────┬─────────┘
             │ (64, 8, 8)
             ▼
    ┌──────────────────┐
    │  STAGE 2: Pattern│  BlockV2 × 2 (mid-level features)
    │  b3: 64→128 s=2  │──→ [Conv→BN→ReLU→Conv→BN] + skip → ReLU
    │  b4: 128→128 s=1 │──→ [Conv→BN→ReLU→Conv→BN] + skip → ReLU
    └────────┬─────────┘
             │ (128, 4, 4)
             ▼
    ┌──────────────────┐
    │  STAGE 3: Semantic│ BlockV3 × 3 (bottleneck, high-level)
    │  b5: 128→256 s=2 │──→ [1×1→3×3→1×1 + BN] + skip → ReLU
    │  b6: 256→256 s=1 │──→ [1×1→3×3→1×1 + BN] + skip → ReLU
    │  b7: 256→512 s=2 │──→ [1×1→3×3→1×1 + BN] + skip → ReLU
    └────────┬─────────┘
             │ (512, 1, 1)
             ▼
    ┌──────────────────┐
    │   CLASSIFIER     │
    │  AdaptiveAvgPool │──→ (512,)
    │  Linear(512→n)   │──→ logits (n classes)
    └──────────────────┘
    """

    def __init__(self, n_class):
        super(NetV1, self).__init__()

        # Stem: 32×32 → 16×16
        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
        )

        # Stage 1: detail features (16×16)
        self.b1 = BlockV1(32, 64, s=1)  # 16×16
        self.b2 = BlockV1(64, 64, s=2)  #  8×8

        # Stage 2: pattern features (8×8 → 4×4)
        self.b3 = BlockV2(64, 128, s=2)  #  4×4
        self.b4 = BlockV2(128, 128, s=1)  #  4×4

        # Stage 3: semantic features (4×4 → 1×1)
        self.b5 = BlockV3(128, 256, s=2)  #  2×2
        self.b6 = BlockV3(256, 256, s=1)  #  2×2
        self.b7 = BlockV3(256, 512, s=2)  #  1×1

        # Classifier
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(512, n_class)

    def forward(self, x):
        x = self.stem(x)

        x = self.b1(x)
        x = self.b2(x)

        x = self.b3(x)
        x = self.b4(x)

        x = self.b5(x)
        x = self.b6(x)
        x = self.b7(x)

        x = self.pool(x)
        x = x.view(x.size(0), -1)

        return self.fc(x)
