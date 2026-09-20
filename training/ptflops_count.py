# -*- coding: utf-8 -*-
"""Đo độ phức tạp tính toán FLOPs / MACs và số lượng tham số của NetV2."""
import os
import sys
import torch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ptflops import get_model_complexity_info
from model.architectures.m2.nets import NetV2

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = NetV2(n_class=10).to(device)

macs, params = get_model_complexity_info(
    model,
    (3, 32, 32),
    as_strings=True,
    print_per_layer_stat=False,
    verbose=False,
    flops_units='GMac'
)

print("=" * 60)
print(f"{'Computational complexity (MACs):':<35} {macs}")
macs_val = float(macs.split()[0])
print(f"{'Floating-point operations (FLOPs):':<35} {macs_val * 2:.3f} GFLOPs")
print(f"{'Number of parameters:':<35} {params}")
print("=" * 60)
