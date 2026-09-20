import torch
import torch.nn as nn


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  UPGRADED: Mọi block tuân theo pattern:                                ║
# ║    Conv → BN → ReLU  +  Residual Skip Connection                       ║
# ║                                                                        ║
# ║  So sánh với bản cũ:                                                   ║
# ║    ❌ Cũ:  Conv → BN → ReLU  (plain, không skip)                       ║
# ║    ✅ Mới: Conv → BN → ReLU → (+skip)                                  ║
# ║                                                                        ║
# ║  Tính W/H:                                                             ║
# ║  - Conv1x1 (K=1, P=0, S=1): luôn giữ nguyên W/H                      ║
# ║  - Conv3x3 (K=3, P=1):                                                ║
# ║      stride=1 → giữ nguyên W/H                                        ║
# ║      stride=2 → W/H giảm nửa                                          ║
# ║                                                                        ║
# ║  Residual: gradient chảy thẳng qua skip → học dễ hơn, không vanishing  ║
# ╚══════════════════════════════════════════════════════════════════════════╝


class BlockV1(nn.Module):
    """
    1 lớp Conv + Residual

    Dùng cho: trích xuất đặc trưng cơ bản (edge, texture)

    Sơ đồ:
                        ┌──────────────────────────────────┐
                        │          skip connection         │
                        │  (Conv1x1 nếu in≠out hoặc s≠1)  │
        x ──────────────┤                                  ▼
        │               │                               [ADD]──→ output
        └→ [Conv3x3(s)] → [BN] → [ReLU] ─────────────────┘

    Tính W/H:  stride=1 → giữ nguyên,  stride=2 → giảm nửa
    """

    def __init__(self, in_channels, out_channels, s):
        super(BlockV1, self).__init__()

        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, stride=s, padding=1, bias=False
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

        # Residual skip: cần adjust khi in_channels≠out_channels hoặc stride≠1
        if in_channels != out_channels or s != 1:
            self.skip = nn.Sequential(
                nn.Conv2d(
                    in_channels, out_channels, kernel_size=1, stride=s, bias=False
                ),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.skip = nn.Identity()

    def forward(self, x):
        identity = self.skip(x)
        out = self.relu(self.bn(self.conv(x)))
        out = out + identity  # residual add
        return out


class BlockV2(nn.Module):
    """
    2 lớp Conv nối tiếp + Residual

    Dùng cho: trích xuất pattern phức tạp hơn (mid-level features)

    Sơ đồ:
                        ┌──────────────────────────────────────────────────┐
                        │                 skip connection                  │
                        │       (Conv1x1 nếu in≠out hoặc s≠1)            │
        x ──────────────┤                                                  ▼
        │               │                                              [ADD]──→ ReLU ──→ out
        └→ [Conv3x3(s)] → [BN] → [ReLU] → [Conv3x3(1)] → [BN] ──────────┘
                                                            (không ReLU trước add!)

    Tính W/H:
        - Conv đầu tiên: stride=s → quyết định kích thước
        - Conv thứ hai:  stride=1 → giữ nguyên
    """

    def __init__(self, in_channels, out_channels, s):
        super(BlockV2, self).__init__()

        self.conv1 = nn.Conv2d(
            in_channels, out_channels, kernel_size=3, stride=s, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)

        self.conv2 = nn.Conv2d(
            out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.relu = nn.ReLU(inplace=True)

        # Residual skip
        if in_channels != out_channels or s != 1:
            self.skip = nn.Sequential(
                nn.Conv2d(
                    in_channels, out_channels, kernel_size=1, stride=s, bias=False
                ),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.skip = nn.Identity()

    def forward(self, x):
        identity = self.skip(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))  # KHÔNG relu ở đây
        out = out + identity  # residual add
        out = self.relu(out)  # ReLU SAU add
        return out


class BlockV3(nn.Module):
    """
    3 lớp Conv nối tiếp (bottleneck) + Residual

    Dùng cho: trích xuất semantic sâu (high-level features)

    Sơ đồ:
                        ┌───────────────────────────────────────────────────────────────┐
                        │                        skip connection                        │
                        │              (Conv1x1 nếu in≠out hoặc s≠1)                  │
        x ──────────────┤                                                               ▼
        │               │                                                           [ADD]──→ ReLU ──→ out
        └→ [Conv1x1] → [BN] → [ReLU]    (nén C → C//2)
          → [Conv3x3(s)] → [BN] → [ReLU]  (spatial, stride=s)
          → [Conv1x1] → [BN] ─────────────────────────────────────────────────────────┘
                          (mở C//2 → C, KHÔNG relu trước add!)

    Tính W/H:
        - Conv1x1 đầu:  K=1 → luôn giữ nguyên W/H
        - Conv3x3 giữa: stride=s → quyết định kích thước
        - Conv1x1 cuối:  K=1 → luôn giữ nguyên W/H
    """

    def __init__(self, in_channels, out_channels, s):
        super(BlockV3, self).__init__()

        mid = out_channels // 2  # nén channels xuống 1/2, mục tiêu để giảm chi phí

        self.conv1 = nn.Conv2d(in_channels, mid, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(mid)

        self.conv2 = nn.Conv2d(mid, mid, kernel_size=3, stride=s, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(mid)

        self.conv3 = nn.Conv2d(mid, out_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(out_channels)

        self.relu = nn.ReLU(inplace=True)

        # Residual skip
        if in_channels != out_channels or s != 1:
            self.skip = nn.Sequential(
                nn.Conv2d(
                    in_channels, out_channels, kernel_size=1, stride=s, bias=False
                ),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.skip = nn.Identity()

    def forward(self, x):
        identity = self.skip(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))  # KHÔNG relu ở đây
        out = out + identity  # residual add
        out = self.relu(out)  # ReLU SAU add
        return out
