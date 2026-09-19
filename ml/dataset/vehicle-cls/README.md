# `vehicle-cls/` — Ảnh phân loại loại xe

> Quyết định chi phối: [ADR-0003](../../../../docs/projects/adrs/0003-duong-du-lieu-vision-tu-phien-do-toi-checkpoint.md)

## Bộ nhãn: đúng 4 lớp

```
motorbike · car · truck · bicycle
```

**[NEVER] tách `car_sedan` với `car_suv`.** Lớp dịch ở biên backend
(`backend/src/infrastructures/Ai/vehicle-type.map.ts`) gộp `car_sedan` · `car_suv` ·
`sedan` · `suv` · `car` về **cùng một** `VehicleCategory.CAR`. Mọi công sức gán nhãn
và mọi tham số model bỏ ra cho khác biệt đó đều bị vứt ngay ở biên. Với
`AI_VEHICLE_IMG_SIZE=32` thì việc tách đó còn gần như bất khả — 32px xoá sạch khác
biệt tỷ lệ thân xe.

Thêm nhãn mới ⇒ **[MUST]** thêm vào `AI_LABEL_TO_CATEGORY` cùng lúc, nếu không
`toVehicleCategory()` trả `null` và backend hiểu là *"không biết"*.

> **[GOTCHA] Runtime chưa khớp schema mục tiêu:**
> `app/config/vision_config.py` hiện mặc định
> `car_sedan,car_suv,motorbike,truck`, trong khi snapshot này chốt
> `motorbike,car,truck,bicycle`. Trước khi nạp checkpoint thật phải đổi
> `AI_VEHICLE_LABELS` đúng thứ tự `class_to_idx` đã lưu trong checkpoint; cùng
> số 4 lớp không có nghĩa index của hai bộ nhãn tương thích.

## Cấu trúc local sau khi materialize

```text
vehicle-cls/
├── README.md
├── dataset.lock.json
└── materialized/           cache local/Colab, không phải nguồn dữ liệu thật
    ├── train/
    │   ├── motorbike/  car/  truck/  bicycle/
    ├── val/
    │   ├── motorbike/  car/  truck/  bicycle/
    └── test-golden/        ⛔ ĐÓNG BĂNG — xem bên dưới
        ├── motorbike/  car/  truck/  bicycle/
```

Git không theo dõi ảnh/thư mục rỗng. Khi chưa có script materialize, có thể dựng
khung thủ công từ `ai/` để thử nghiệm:

```bash
mkdir -p ml/dataset/vehicle-cls/materialized
for split in train val test-golden; do
  mkdir -p ml/dataset/vehicle-cls/materialized/$split/{motorbike,car,truck,bicycle}
done
```

Layout này khớp `torchvision.datasets.ImageFolder`. Tuy nhiên **chưa chạy lệnh
train production bằng README này**: `training/train_imagefolder.py` hiện suy số
lớp từ `--dataset` (`cifar10` → 10, `cifar100` → 100, giá trị khác → 30), trong
khi task này có 4 lớp. Truyền
`--data ./ml/dataset/vehicle-cls/materialized` không tự sửa số lớp, nên
checkpoint sinh ra có output head sai.

Trước lần train thật cần sửa script để lấy `class_to_idx` từ train set, kiểm
train/val có cùng thứ tự lớp và ghi mapping đó vào checkpoint. Sau đó mới công
bố câu lệnh chuẩn tại đây.

## ⛔ `test-golden/` — đóng băng

**[NEVER] train lên tập này, dù chỉ một lần.** Ảnh đã thấy lúc train thì điểm đo trên
nó là điểm giả, và ta sẽ tin vào một con số không có thật.

Tách ra **trước** khi train lần đầu, rồi để yên. Mọi thay đổi model hay tham số đều
báo cáo số **trước và sau** trên đúng tập này.

## Ảnh đến từ đâu

Từ phiên đỗ thật — `parking_session.check_in_image_url` / `check_out_image_url`, kèm
`ai_confidence_in/out`. Phần thu thập đã dựng trong ISSUE-003.

Nhãn đến từ **vòng active learning**: khi nhân viên sửa tay một kết quả AI đoán sai,
đó là nhãn do người gán — miễn phí và đúng phân phối thật (SUGGESTION-007 C1). Ưu tiên kéo
về những lượt `ai_confidence` thấp hoặc bị sửa, vì đó là chỗ model đang yếu.

> **[GOTCHA] Chưa chạy migration trên Production = chưa có ảnh nào được lưu.** Bốn cột
> kia chính là thứ bắt ảnh lại. Mỗi phiên xe đi qua khi cột chưa tồn tại là một mẫu
> huấn luyện mất vĩnh viễn — không quay lại lấy được.

## `dataset.lock.json` — dấu vân tay snapshot được phép vào Git

Ghi hash, label, split và group hash của từng mẫu. Không có nó thì không trả lời
được câu *"con số 91% hồi đó đo trên tập nào"*. Object key/capture ID nằm trong
private manifest; lock trong Git không chứa signed URL, biển số hay định danh
người dùng.

Tối thiểu lock cần có: `schema_version`, `dataset_id`, `task`, `label_schema`,
`source_cutoff`, `split_policy`, `preprocessing` và `splits`. Mỗi checkpoint phải
copy đúng lock của lần train vào folder run, không tham chiếu mơ hồ tới lock
“mới nhất”.

## Ba công cụ còn thiếu trước khi train thật

| Script đề xuất | Vai trò |
|---|---|
| `training/materialize_dataset.py` | Tải đúng object version theo private manifest và dựng ImageFolder |
| `training/validate_dataset.py` | Kiểm hash trùng, ảnh hỏng, nhãn, cân bằng lớp và group leakage |
| `training/eval_vehicle_classifier.py` | Đo test-golden, per-class metric và confusion matrix |

Không tạo file rỗng để giữ chỗ. Mỗi script được thêm cùng phase triển khai và
phải có input/output kiểm chứng được.
