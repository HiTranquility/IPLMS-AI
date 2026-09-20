# -*- coding: utf-8 -*-
"""Kiem tra cau truc mo hinh, so luong tham so va bang tom tat layers."""
import os
import sys
import torch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from torchsummary import summary
from model.architectures.m1.nets import NetV1
from model.architectures.m2.nets import NetV2

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}\n")

# Khoi tao mo hinh
model_v1 = NetV1(n_class=10).to(device)
model_v2 = NetV2(n_class=10).to(device)

print("=" * 60)
print("[*] NetV1 (Midterm Model) Parameter Count:")
params_v1 = sum(p.numel() for p in model_v1.parameters())
print(f"Total parameters: {params_v1:,}")

print("=" * 60)
print("[*] NetV2 (Final Model with SE Attention) Parameter Count:")
params_v2 = sum(p.numel() for p in model_v2.parameters())
print(f"Total parameters: {params_v2:,}")

print("\n" + "=" * 60)
print("[*] Summary NetV2 (Input: 3, 32, 32):")
summary(model_v2, (3, 32, 32), device=str(device))
