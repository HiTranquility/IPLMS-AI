#!/usr/bin/env python3
"""
Đánh giá model trên Test Set độc lập (không được sử dụng lúc training).
Test set cung cấp đánh giá công bằng về khả năng generalization của model.
"""

import os
import torch
import torch.nn as nn
import torch.utils.data
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import argparse
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.architectures.m1.nets import NetV1

# Italian -> English class names
ANIMAL10_IT_TO_EN = {
    'cane': 'dog',
    'cavallo': 'horse',
    'elefante': 'elephant',
    'farfalla': 'butterfly',
    'gallina': 'chicken',
    'gatto': 'cat',
    'mucca': 'cow',
    'pecora': 'sheep',
    'ragno': 'spider',
    'scoiattolo': 'squirrel'
}

def get_args():
    parser = argparse.ArgumentParser(description='Evaluate NetV1 on Animal-10 Test Set')
    parser.add_argument('-r', '--data', type=str, default='./model/dataset/Animal-10',
                        help='Path to Animal-10 dataset')
    # `Phat/` là tàn dư của cách chia theo TÊN SINH VIÊN đã bỏ (xem model/README.md).
    # Giữ nguyên tên thư mục vì đổi nó là trỏ sang chỗ khác, không phải đổi layout.
    parser.add_argument('--checkpoint', type=str, default='./model/checkpoint/Phat/model_best32.pth.tar',
                        help='Path to model checkpoint')
    parser.add_argument('-b', '--batch-size', default=128, type=int,
                        help='Batch size for evaluation')
    parser.add_argument('-j', '--workers', default=4, type=int,
                        help='Number of data loading workers')
    parser.add_argument('--img-size', default=32, type=int,
                        choices=[32, 224],
                        help='Input image size (32 or 224)')
    parser.add_argument('-g', '--gpu', default=0, type=int,
                        help='GPU id to use. Set to -1 for CPU')
    return parser.parse_args()

def load_checkpoint(checkpoint_path, device):
    """Load model from checkpoint"""
    print(f"Loading checkpoint from {checkpoint_path}...")
    # torch>=2.6 mặc định weights_only=True; checkpoint do chính ta train (xem train_imagefolder.py).
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    state_dict = checkpoint.get('state_dict', checkpoint)
    
    # Remove 'module.' prefix if present (from DataParallel)
    new_state_dict = {}
    for k, v in state_dict.items():
        if k.startswith('module.'):
            new_state_dict[k[7:]] = v
        else:
            new_state_dict[k] = v
    
    return new_state_dict

def get_class_names(dataset):
    """Get class names from dataset"""
    classes = dataset.classes
    # Translate Italian names to English for Animal-10
    classes_en = [ANIMAL10_IT_TO_EN.get(c, c) for c in classes]
    return classes_en

class AverageMeter:
    """Computes and stores the average and current value"""
    def __init__(self, name, fmt=':f'):
        self.name = name
        self.fmt = fmt
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

    def __str__(self):
        fmtstr = '{name} {val' + self.fmt + '} ({avg' + self.fmt + '})'
        return fmtstr.format(**self.__dict__)

def accuracy(output, target, topk=(1,)):
    """Computes the accuracy over the k top predictions"""
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].reshape(-1).float().sum(0, keepdim=True)
            acc = correct_k.mul_(1.0 / batch_size)
            res.append(acc)
        return res

def evaluate(model, test_loader, device, num_classes):
    """Evaluate model on test set"""
    model.eval()
    
    top1 = AverageMeter('Top1-Acc')
    top5 = AverageMeter('Top5-Acc') if num_classes >= 5 else None
    
    print("\n🔍 Evaluating on Test Set...")
    print("-" * 60)
    
    with torch.no_grad():
        for batch_idx, (input, target) in enumerate(test_loader):
            input = input.to(device)
            target = target.to(device)
            
            # Forward pass
            output = model(input)
            
            # Compute accuracy
            acc1, = accuracy(output, target, topk=(1,))
            top1.update(acc1.item(), input.size(0))
            
            if top5 and num_classes >= 5:
                _, acc5 = accuracy(output, target, topk=(1, 5))
                top5.update(acc5.item(), input.size(0))
            
            if (batch_idx + 1) % 10 == 0 or batch_idx == 0:
                msg = f"[{batch_idx + 1}/{len(test_loader)}] Top1: {top1.avg:.3f}"
                if top5 and num_classes >= 5:
                    msg += f" | Top5: {top5.avg:.3f}"
                print(msg)
    
    print("-" * 60)
    print(f"\n✅ TEST RESULTS:")
    print(f"   Top-1 Accuracy: {top1.avg:.2%}")
    if top5 and num_classes >= 5:
        print(f"   Top-5 Accuracy: {top5.avg:.2%}")
    print()
    
    return top1.avg

def main():
    args = get_args()
    
    # Device
    if args.gpu >= 0:
        device = torch.device(f'cuda:{args.gpu}')
    else:
        device = torch.device('cpu')
    print(f"Device: {device}")
    
    # Data transforms
    if args.img_size == 32:
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    else:  # 224
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    # Load test dataset
    test_path = os.path.join(args.data, 'test')
    if not os.path.exists(test_path):
        print(f"❌ Test folder not found: {test_path}")
        print(f"   Please run 'python split_data.py' first to create train/val/test split")
        return
    
    test_dataset = datasets.ImageFolder(test_path, transform=transform)
    test_loader = torch.utils.data.DataLoader(
        test_dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=True
    )
    
    num_classes = len(test_dataset.classes)
    print(f"\n📊 Dataset Info:")
    print(f"   Classes: {num_classes}")
    print(f"   Test samples: {len(test_dataset)}")
    print(f"   Class names: {test_dataset.classes}")
    class_names = get_class_names(test_dataset)
    print(f"   English names: {class_names}")
    
    # Load model
    state_dict = load_checkpoint(args.checkpoint, device)
    
    # Infer num_classes from checkpoint
    fc_out_features = state_dict['fc.weight'].shape[0]
    print(f"\n🏗️  Model Info:")
    print(f"   Checkpoint output classes: {fc_out_features}")
    print(f"   Test set classes: {num_classes}")
    
    if fc_out_features != num_classes:
        print(f"\n⚠️  WARNING: Mismatch detected!")
        print(f"   Model expects {fc_out_features} classes but test set has {num_classes}")
        print(f"   This may affect accuracy evaluation.")
    
    # Create model with correct num_classes
    model = NetV1(num_classes=fc_out_features)
    model.load_state_dict(state_dict, strict=False)
    model = model.to(device)
    
    # Evaluate
    top1_acc = evaluate(model, test_loader, device, num_classes)

if __name__ == '__main__':
    main()
