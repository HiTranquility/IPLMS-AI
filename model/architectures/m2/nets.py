from model.architectures.m2.backbones import *


class NetV2(nn.Module):
    """
    M2: Improved from M1 (NetV1).

    Changes vs M1:
    - SE Attention on ALL stages (M1 only had SE on stage 2)
    - Bottleneck block (BlockV3) for deeper semantic extraction
    - Dropout before classifier to reduce overfitting
    - bias=False on all conv layers (BN handles bias)
    - Deeper: 8 blocks vs M1's 7 blocks
    """
    def __init__(self, n_class):
        super().__init__()

        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True)
        )

        # Stage 1: local features (edges, textures)
        self.stage1 = nn.Sequential(
            BlockV1(32, 64, stride=1),
            BlockV1(64, 64, stride=2),
        )

        # Stage 2: mid-level patterns (efficient depthwise sep)
        self.stage2 = nn.Sequential(
            BlockV2(64, 128, stride=2),
            BlockV2(128, 128, stride=1),
        )

        # Stage 3: high-level semantic (bottleneck)
        self.stage3 = nn.Sequential(
            BlockV3(128, 256, stride=2),
            BlockV3(256, 256, stride=1),
        )

        # Stage 4: final representation
        self.stage4 = nn.Sequential(
            BlockV3(256, 512, stride=2),
            BlockV3(512, 512, stride=1),
        )

        self.pool = nn.AdaptiveAvgPool2d(1)
        self.drop = nn.Dropout(0.2)
        self.fc = nn.Linear(512, n_class)

    def forward(self, x):
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.stage4(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.drop(x)
        return self.fc(x)
