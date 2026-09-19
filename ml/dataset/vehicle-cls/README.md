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

## Cấu trúc

```text
vehicle-cls/
├── raw/                    ảnh kéo từ phiên đỗ, CHƯA gán nhãn
├── train/
│   ├── motorbike/  car/  truck/  bicycle/
├── val/
│   ├── motorbike/  car/  truck/  bicycle/
└── test-golden/            ⛔ ĐÓNG BĂNG — xem bên dưới
    ├── motorbike/  car/  truck/  bicycle/
```

Git không theo dõi được thư mục rỗng, nên sau khi clone phải dựng lại khung — chạy
từ `ai/`:

```bash
mkdir -p ml/dataset/vehicle-cls/raw
for split in train val test-golden; do
  mkdir -p ml/dataset/vehicle-cls/$split/{motorbike,car,truck,bicycle}
done
```

Layout này khớp `torchvision.datasets.ImageFolder`, nên dùng thẳng được:

```bash
cd ai
python training/train_imagefolder.py \
  --data ./ml/dataset/vehicle-cls --net NetV2 --img-size 32 --epochs 100
```

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

## `dataset.lock.json` — file duy nhất ở đây vào git

Ghi hash của từng ảnh theo tập. Không có nó thì không trả lời được câu
*"con số 91% hồi đó đo trên tập nào"*, và không tái lập được kết quả cũ.
