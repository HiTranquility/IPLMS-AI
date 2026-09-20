# 🏋️ `training/` — Huấn luyện & Kiểm tra Model (ghi nhớ cách chạy)

Script train/eval cho CNN phân loại ảnh ở [`../model`](../model) (code bên thứ ba), đã sửa import cho layout `ai/`.
Model: `NetV1` (M1) ở [`../model/architectures/m1`](../model/architectures/m1), `NetV2` (M2) ở [`../model/architectures/m2`](../model/architectures/m2).

> **Chạy từ đâu?** Luôn `cd ai` rồi gọi `python training/<script>.py`. Mỗi script tự thêm `ai/` vào `sys.path` nên `from model...` chạy được. Dataset/checkpoint mặc định nằm ở `ai/model/dataset/` và `ai/model/checkpoint/` (đều gitignored).
>
> Bản đồ dữ liệu/artifact: [`model/README.md`](../model/README.md) · Runbook GPU:
> [Google Colab](../docs/guides/06-google-colab-training-runbook.md).

## 0. Cài đặt (1 lần)

```bash
cd ai
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash; *nix: .venv/bin/activate
pip install -r requirements.txt
```

## 1. Chuẩn bị dữ liệu

**CIFAR-10 / CIFAR-100 (cho NetV2 — Final):** tải tự động, không cần chuẩn bị tay:
```bash
python training/train_cifar.py -d cifar10 --download -e 1   # lần đầu thêm --download
```

**Animal-10 (cho NetV1 — Midterm, dùng ImageFolder):**
1. Tải [Animal-10](https://www.kaggle.com/datasets/alessiocorrado99/animals10) → giải nén vào `ai/model/dataset/Animal-10/` (có `raw-img/`).
2. Chia train/val 80/20:
   ```bash
   python training/split_data.py
   ```

## 2. Train

```bash
# NetV2 (Final) trên CIFAR-10 — 200 epoch
python training/train_cifar.py -d cifar10 --download -e 200
# NetV2 trên CIFAR-100
python training/train_cifar.py -d cifar100 --download -e 200

# NetV1 (Midterm) trên Animal-10 — 32x32, 100 epoch
python training/train_imagefolder.py --data ./model/dataset/Animal-10 --net NetV1 --img-size 32 --epochs 100
```

Tham số hay dùng (`train_cifar.py`): `-d` dataset · `-e` epochs · `-b` batch (128) · `-l` lr (0.1) · `-s` LR milestones (100 150 180) · `-g` GPU id (-1 = CPU).
Tham số `train_imagefolder.py`: `--net NetV1|NetV2` · `--img-size` · `--epochs` · `-e` (chỉ evaluate).

## 3. Kết quả lưu ở đâu?

```
ai/model/checkpoint/<dataset>_<size>_<Net>/
├── <Net>.txt               # log accuracy/loss mỗi epoch
├── model_best.pth.tar      # (M1) checkpoint val acc tốt nhất — key: state_dict
├── checkpoint.pth.tar      # (M1) epoch cuối
└── checkpoint_epochXXXX.pth # (M2) — key: model_state_dict
```
Chi tiết định dạng key checkpoint: [`../checkpoint_config_guide.md`](../checkpoint_config_guide.md).

## 4. Xem / kiểm tra model

```bash
# In kiến trúc + số tham số + torchsummary
python training/checkmodel.py

# Đếm FLOPs / MACs / params (NetV2)
python training/ptflops_count.py

# Vẽ biểu đồ accuracy & loss từ log (sửa CHECKPOINT_DIR trong file trước khi chạy)
python training/draw_graph.py

# Đánh giá NetV1 trên test set Animal-10
python training/test_animal10.py
```

## 4b. Đo độ chính xác ĐỌC BIỂN SỐ (khác hẳn phần trên)

Mục 1–4 nói về **CNN phân loại ảnh** (NetV1/NetV2). Phần đọc **biển số** do
YOLO + EasyOCR đảm nhiệm và **không train ở đây** — nhưng vẫn phải **đo được**,
nếu không mọi thay đổi pipeline sau này đều là cảm tính (SUGGESTION-007 · B1).

```bash
cd ai
# 1. Nạp dataset công khai đã tải về vào bộ vàng
python training/import_plate_dataset.py --from filename --src ~/Downloads/vn-plates

# 2. Đo
python training/eval_plates.py --label before-B2
```

Bộ vàng + cách đọc từng chỉ số: [`../data/golden/plates/README.md`](../data/golden/plates/README.md).

**[MUST]** PR nào đụng `anpr_engine.py` hoặc đổi `model/artifacts/bootstrap/anpr/best.pt` phải kèm số
**trước và sau** trên cùng bộ vàng. Không có số ⇒ không biết là tốt lên hay tệ đi.

**[GOTCHA]** Chỉ số `exact_match_strict` và `exact_match_relaxed` chênh nhau bao
nhiêu thì đúng bấy nhiêu là phần **hậu xử lý định dạng biển VN** (B2) lấy về
được mà không cần đổi model — OCR đang đọc đúng ký tự nhưng rụng dấu phân cách,
và backend tra xe bằng so khớp chuỗi chính xác nên rụng dấu = không khớp.

## 5. Đưa model đã train vào dịch vụ ANPR

CNN này là **bộ phân loại ảnh** — trong dịch vụ nó chỉ dùng làm **tầng phân loại loại xe (optional)**. Để bật:
1. Sửa `train_imagefolder.py` để suy `n_class` + `class_to_idx` từ ImageFolder
   và lưu mapping vào checkpoint. Hiện script suy số lớp từ `--dataset`, nên
   chưa an toàn để train snapshot `vehicle-cls` 4 lớp.
2. Train (hoặc fine-tune) trên tập ảnh **loại xe** đúng 4 lớp đã chốt.
3. Trỏ service tới checkpoint local hoặc artifact đã được duyệt (xem [`../README.md`](../README.md)):
   ```bash
   AI_VEHICLE_CHECKPOINT=/path/to/checkpoint.pth AI_VEHICLE_LABELS=car,motorbike
   ```
   Với object storage, đặt `AI_VEHICLE_ARTIFACT_URL`, `AI_VEHICLE_ARTIFACT_SHA256`
   và `AI_VEHICLE_MODEL_VERSION`; URL chỉ là quyền tải ngắn hạn, version + hash
   mới là định danh bền của model.
Phần nhận diện **biển số** do YOLO+EasyOCR trong [`../app/core/vision/engines/anpr_engine.py`](../app/core/vision/engines/anpr_engine.py) đảm nhiệm (không cần train lại ở đây; weights `best.pt` đã có sẵn).

> **[GOTCHA] Đừng train phân biệt sedan với SUV — lớp dịch vứt bỏ khác biệt đó.**
> Hai đầu **cố ý** nói hai từ vựng: AI trả nhãn của model, backend sống bằng
> `VehicleCategory`. Lớp dịch đã có ở biên backend
> (`backend/src/infrastructures/Ai/vehicle-type.map.ts`, dựng trong ISSUE-003), và nó
> gộp `car_sedan` · `car_suv` · `sedan` · `suv` · `car` → **cùng một** `CAR`.
>
> Nghĩa là mọi công sức gán nhãn và mọi tham số model bỏ ra để tách sedan/SUV đều bị
> vứt ngay ở biên. Với `AI_VEHICLE_IMG_SIZE=32` thì việc đó còn gần như bất khả — 32px
> xoá sạch khác biệt tỷ lệ thân xe.
>
> **Nên train đúng 4 lớp sống sót 1:1 qua lớp dịch:** `motorbike` · `car` · `truck` ·
> `bicycle`. Chúng khác nhau ở hình khối tổng thể nên 32×32 vẫn kham được. Thêm nhãn
> mới ngoài 4 cái này thì phải thêm vào `AI_LABEL_TO_CATEGORY`, nếu không
> `toVehicleCategory()` trả `null` và backend hiểu là "không biết".

## 📄 Danh sách script

| Script | Việc |
|---|---|
| `train_cifar.py` | Train NetV2 trên CIFAR-10/100 (tải tự động) |
| `train_imagefolder.py` | Train NetV1/NetV2 trên ImageFolder (Animal-10) |
| `test_animal10.py` | Eval NetV1 trên test set Animal-10 |
| `checkmodel.py` | In kiến trúc + summary |
| `ptflops_count.py` | Đếm FLOPs/MACs/params |
| `draw_graph.py` | Vẽ biểu đồ acc/loss từ log |
| `prepare_cifar.py` | Tạo CIFAR ImageFolder (cho train_imagefolder) |
| `split_data.py` | Chia Animal-10 raw-img → train/val |
| `writeLogAcc.py` · `calculate_w_h.py` | Tiện ích (ghi log / tính W-H feature map) |
| `import_plate_dataset.py` | Nạp dataset biển số công khai → bộ vàng (`data/golden/plates/`) |
| `eval_plates.py` | Đo `exact-match` / CER / latency của pipeline đọc biển trên bộ vàng |
| `plate_metrics.py` | Hàm thuần tính CER / exact-match (không nạp model — `test/` import được) |
| `materialize_dataset.py` | Scaffold CLI: materialize snapshot từ object storage |
| `validate_dataset.py` | Scaffold CLI: kiểm hash/schema/leakage trước train |
| `train_vehicle_classifier.py` | Scaffold CLI chuẩn cho local/Colab |
| `eval_vehicle_classifier.py` | Scaffold CLI đánh giá classifier trên test-golden |
| `package_model.py` | Scaffold CLI đóng gói candidate + manifest/checksum |
| `publish_model.py` | Scaffold CLI publish version bất biến; chưa đổi accepted alias |

Sáu CLI scaffold trên hỗ trợ `--status` và cố ý dừng nếu chạy như một pipeline
thật. Chúng là mốc công việc đã lưu trong repo, chưa phải tuyên bố pipeline train
đã hoàn chỉnh.
