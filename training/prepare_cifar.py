"""
Download CIFAR-10 and CIFAR-100, then export to ImageFolder format:
    datasets/CIFAR10/train/<class_name>/xxx.png
    datasets/CIFAR10/val/<class_name>/xxx.png
    datasets/CIFAR100/train/<class_name>/xxx.png
    datasets/CIFAR100/val/<class_name>/xxx.png

Usage:
    python prepare_cifar.py              # both CIFAR-10 and CIFAR-100
    python prepare_cifar.py --cifar10    # only CIFAR-10
    python prepare_cifar.py --cifar100   # only CIFAR-100
"""

import os
import argparse
from PIL import Image
import torchvision.datasets as datasets

def export_to_imagefolder(dataset, root_dir, class_names):
    os.makedirs(root_dir, exist_ok=True)
    counts = {}
    for idx, (img, label) in enumerate(dataset):
        class_name = class_names[label]
        class_dir = os.path.join(root_dir, class_name)
        os.makedirs(class_dir, exist_ok=True)

        counts[class_name] = counts.get(class_name, 0) + 1
        img_path = os.path.join(class_dir, f'{counts[class_name]:05d}.png')
        if isinstance(img, Image.Image):
            img.save(img_path)
        else:
            Image.fromarray(img).save(img_path)

        if (idx + 1) % 5000 == 0:
            print(f'  {idx + 1}/{len(dataset)} images exported...')

    print(f'  Done: {idx + 1} images -> {root_dir}')


def prepare_cifar10(base='./ml/dataset/CIFAR10'):
    print('=== CIFAR-10 ===')
    print('Downloading CIFAR-10...')
    train_set = datasets.CIFAR10(root='./ml/dataset/_raw', train=True, download=True)
    test_set  = datasets.CIFAR10(root='./ml/dataset/_raw', train=False, download=True)
    class_names = train_set.classes

    print(f'Classes: {class_names}')
    print(f'Train: {len(train_set)}, Val: {len(test_set)}')

    print('Exporting train set...')
    export_to_imagefolder(train_set, os.path.join(base, 'train'), class_names)
    print('Exporting val set...')
    export_to_imagefolder(test_set, os.path.join(base, 'val'), class_names)
    print(f'CIFAR-10 ready at {base}\n')


def prepare_cifar100(base='./ml/dataset/CIFAR100'):
    print('=== CIFAR-100 ===')
    print('Downloading CIFAR-100...')
    train_set = datasets.CIFAR100(root='./ml/dataset/_raw', train=True, download=True)
    test_set  = datasets.CIFAR100(root='./ml/dataset/_raw', train=False, download=True)
    class_names = train_set.classes

    print(f'Classes ({len(class_names)}): {class_names[:10]}... ')
    print(f'Train: {len(train_set)}, Val: {len(test_set)}')

    print('Exporting train set...')
    export_to_imagefolder(train_set, os.path.join(base, 'train'), class_names)
    print('Exporting val set...')
    export_to_imagefolder(test_set, os.path.join(base, 'val'), class_names)
    print(f'CIFAR-100 ready at {base}\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cifar10', action='store_true', help='only CIFAR-10')
    parser.add_argument('--cifar100', action='store_true', help='only CIFAR-100')
    args = parser.parse_args()

    do_both = not args.cifar10 and not args.cifar100

    if do_both or args.cifar10:
        prepare_cifar10()
    if do_both or args.cifar100:
        prepare_cifar100()

    print('All done!')
