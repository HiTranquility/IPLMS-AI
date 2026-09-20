import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import numpy as np
import re
import os
import sys

# ╔══════════════════════════════════════════════════════════╗
# ║  CHỈ CẦN ĐỔI DÒNG NÀY                                 ║
# ╚══════════════════════════════════════════════════════════╝
CHECKPOINT_DIR = 'model/checkpoint/cifar10_32x32_BTImages10_Phat_NetV1_V1'

# ── Auto-detect log file ──
def find_log_file(checkpoint_dir):
    skip = {'Loss_plot.txt', 'train_prec1.txt', 'train_prec5.txt',
            'val_prec1.txt', 'val_prec5.txt'}
    for f in os.listdir(checkpoint_dir):
        if f.endswith('.txt') and f not in skip:
            return os.path.join(checkpoint_dir, f)
    return None

def parse_log(filepath):
    pattern = re.compile(
        r'Epoch (\d+)/(\d+) summary: '
        r'loss_train=([\d.]+), acc_train=([\d.]+)%, '
        r'loss_val=([\d.]+), acc_val=([\d.]+)%'
    )
    data = {'epoch': [], 'total_epochs': 0,
            'loss_train': [], 'acc_train': [],
            'loss_val': [], 'acc_val': []}

    with open(filepath, 'r') as f:
        for line in f:
            m = pattern.search(line)
            if m:
                data['epoch'].append(int(m.group(1)))
                data['total_epochs'] = int(m.group(2))
                data['loss_train'].append(float(m.group(3)))
                data['acc_train'].append(float(m.group(4)))
                data['loss_val'].append(float(m.group(5)))
                data['acc_val'].append(float(m.group(6)))
    return data

log_path = find_log_file(CHECKPOINT_DIR)
if log_path is None:
    print(f"No log file found in {CHECKPOINT_DIR}")
    sys.exit(1)

print(f"Reading: {log_path}")
data = parse_log(log_path)

epochs     = data['epoch']
acc_train  = data['acc_train']
acc_val    = data['acc_val']
loss_train = data['loss_train']
loss_val   = data['loss_val']
total_ep   = data['total_epochs']
run_name   = os.path.basename(CHECKPOINT_DIR)

gap = np.array(acc_train) - np.array(acc_val)
best_val_epoch = int(np.argmax(acc_val))
best_val_acc   = acc_val[best_val_epoch]

# Auto-detect LR drop: find epoch where train_loss drops > 30% in one step
lr_drops = []
for i in range(1, len(loss_train)):
    if loss_train[i] < loss_train[i-1] * 0.70:
        lr_drops.append(epochs[i])

# ── Theme ──
BG     = '#0f1117'
PANEL  = '#181b25'
GRID_C = '#2a2d3a'
TEXT   = '#c8cad0'
TRAIN  = '#6ee7b7'
VAL    = '#f472b6'
GAP_C  = '#fbbf24'
ACCENT = '#818cf8'

plt.rcParams.update({
    'text.color': TEXT, 'axes.labelcolor': TEXT,
    'xtick.color': TEXT, 'ytick.color': TEXT,
    'figure.facecolor': BG, 'axes.facecolor': PANEL,
    'axes.edgecolor': GRID_C,
    'grid.color': GRID_C, 'grid.linestyle': '-',
    'grid.alpha': 0.5, 'grid.linewidth': 0.5,
    'font.family': 'sans-serif', 'font.size': 10,
})

fig = plt.figure(figsize=(18, 10))
gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.30,
              left=0.06, right=0.97, top=0.90, bottom=0.08)

ax_acc  = fig.add_subplot(gs[0, 0:2])
ax_loss = fig.add_subplot(gs[1, 0:2])
ax_gap  = fig.add_subplot(gs[0, 2])
ax_info = fig.add_subplot(gs[1, 2])

fig.suptitle(run_name, fontsize=18, fontweight='bold', color='white', y=0.96)

# ═══════════════ ACCURACY ═══════════════
ax_acc.plot(epochs, acc_train, color=TRAIN, linewidth=2, label='Train', zorder=3)
ax_acc.plot(epochs, acc_val, color=VAL, linewidth=2, label='Val', zorder=3)
ax_acc.fill_between(epochs, acc_train, alpha=0.10, color=TRAIN)
ax_acc.fill_between(epochs, acc_val, alpha=0.10, color=VAL)

ax_acc.scatter(best_val_epoch, best_val_acc, s=100, color=VAL,
               edgecolors='white', linewidths=1.5, zorder=5)
ax_acc.annotate(f'{best_val_acc:.2f}%  (ep {best_val_epoch})',
                xy=(best_val_epoch, best_val_acc),
                xytext=(best_val_epoch - max(len(epochs)//5, 3), best_val_acc - 12),
                fontsize=9, fontweight='bold', color=VAL,
                arrowprops=dict(arrowstyle='->', color=VAL, lw=1.2),
                bbox=dict(boxstyle='round,pad=0.3', facecolor=PANEL,
                          edgecolor=VAL, alpha=0.95))

for d in lr_drops:
    ax_acc.axvline(x=d, color=ACCENT, linestyle=':', linewidth=1, alpha=0.7)
    ax_acc.text(d + 0.5, min(acc_val) - 2, 'LR drop', fontsize=8, color=ACCENT, alpha=0.8)

ax_acc.set_title('Accuracy', fontsize=13, fontweight='bold', color='white', pad=10)
ax_acc.set_xlabel('Epoch')
ax_acc.set_ylabel('Accuracy (%)')
ax_acc.set_ylim(min(min(acc_train), min(acc_val)) - 5, 102)
ax_acc.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
ax_acc.legend(loc='lower right', fancybox=True, framealpha=0.6,
              edgecolor=GRID_C, facecolor=PANEL)
ax_acc.grid(True)

# ═══════════════ LOSS ═══════════════
ax_loss.plot(epochs, loss_train, color=TRAIN, linewidth=2, label='Train', zorder=3)
ax_loss.plot(epochs, loss_val, color=VAL, linewidth=2, label='Val', zorder=3)
ax_loss.fill_between(epochs, loss_train, alpha=0.10, color=TRAIN)
ax_loss.fill_between(epochs, loss_val, alpha=0.10, color=VAL)

for d in lr_drops:
    ax_loss.axvline(x=d, color=ACCENT, linestyle=':', linewidth=1, alpha=0.7)
    ax_loss.text(d + 0.5, max(loss_val) * 0.92, 'LR drop', fontsize=8, color=ACCENT, alpha=0.8)

ax_loss.set_title('Loss', fontsize=13, fontweight='bold', color='white', pad=10)
ax_loss.set_xlabel('Epoch')
ax_loss.set_ylabel('Loss')
ax_loss.legend(loc='upper right', fancybox=True, framealpha=0.6,
               edgecolor=GRID_C, facecolor=PANEL)
ax_loss.grid(True)

# ═══════════════ GAP ═══════════════
colors_gap = [GAP_C if g >= 0 else '#ef4444' for g in gap]
ax_gap.bar(epochs, gap, color=colors_gap, alpha=0.7, width=0.8, edgecolor='none')
ax_gap.axhline(y=0, color=TEXT, linewidth=0.5, alpha=0.3)
ax_gap.set_title('Train\u2212Val Gap', fontsize=13, fontweight='bold', color='white', pad=10)
ax_gap.set_xlabel('Epoch')
ax_gap.set_ylabel('Gap (%)')
ax_gap.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
ax_gap.grid(True, axis='y')

# ═══════════════ INFO PANEL ═══════════════
ax_info.axis('off')

info_items = [
    ('Run',            run_name),
    ('Progress',       f'{len(epochs)} / {total_ep} epochs'),
    ('',               ''),
    ('Train Acc',      f'{acc_train[-1]:.2f}%'),
    ('Val Acc',        f'{acc_val[-1]:.2f}%'),
    ('Best Val Acc',   f'{best_val_acc:.2f}%  (ep {best_val_epoch})'),
    ('',               ''),
    ('Train Loss',     f'{loss_train[-1]:.5f}'),
    ('Val Loss',       f'{loss_val[-1]:.5f}'),
    ('Gap (last)',     f'{gap[-1]:.2f}%'),
]

y_start = 0.92
for i, (label, value) in enumerate(info_items):
    y = y_start - i * 0.085
    if label == '':
        ax_info.plot([0.05, 0.95], [y + 0.04, y + 0.04],
                     color=GRID_C, linewidth=0.5, transform=ax_info.transAxes, clip_on=False)
        continue
    ax_info.text(0.08, y, label, fontsize=10, color='#888899',
                 transform=ax_info.transAxes, va='center')
    ax_info.text(0.92, y, value, fontsize=10, color='white', fontweight='bold',
                 transform=ax_info.transAxes, va='center', ha='right')

box = plt.Rectangle((0.02, 0.02), 0.96, 0.96, transform=ax_info.transAxes,
                     facecolor=PANEL, edgecolor=GRID_C, linewidth=1, clip_on=False)
ax_info.add_patch(box)
ax_info.set_zorder(-1)

out_path = os.path.join(CHECKPOINT_DIR, 'training_dashboard.png')
plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()
print(f"Saved to {out_path}")
