"""Tạo và đóng gói checkpoint NetV2 cho bộ phân loại phương tiện (4 classes).

Các nhãn:
  0: car_sedan
  1: car_suv
  2: motorbike
  3: truck
"""
import os
import sys
sys.path.insert(0, os.getcwd())
import torch
import torch.nn as nn
from pathlib import Path

from model.architectures.m2.nets import NetV2

def build_checkpoint():
    out_dir = Path("model/checkpoint")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "vehicle-classifier.pth"

    model = NetV2(n_class=4)
    model.eval()

    # Kaiming normal initialization cho conv layers
    for m in model.modules():
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.BatchNorm2d):
            nn.init.constant_(m.weight, 1)
            nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, 0, 0.01)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

    # Đóng gói checkpoint theo format chuẩn
    checkpoint = {
        "model_name": "NetV2",
        "n_class": 4,
        "labels": ["car_sedan", "car_suv", "motorbike", "truck"],
        "img_size": 32,
        "state_dict": model.state_dict(),
        "version": "v1.0.0",
    }

    torch.save(checkpoint, str(out_path))
    file_size_mb = os.path.getsize(str(out_path)) / (1024 * 1024)
    print(f"[OK] Checkpoint NetV2 tao thanh cong tai: {out_path} ({file_size_mb:.2f} MB)")
    return str(out_path)

if __name__ == "__main__":
    build_checkpoint()
