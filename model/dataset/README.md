# `model/dataset/` — các snapshot huấn luyện đã vật hoá

> Luật đầy đủ: [ADR-0003](../../../docs/projects/adrs/09-2026/0003-duong-du-lieu-vision-tu-phien-do-toi-checkpoint.md)
> Bản đồ tổng thể: [`model/README.md`](../README.md)

Đây là workspace local mà PyTorch đọc, không phải nơi backend upload ảnh trực
tiếp và không phải datalake production. Dữ liệu nguồn nằm trong object storage
private + catalog; một snapshot được duyệt mới được materialize vào đây.

`dataset/` dùng số ít theo tên loại tài nguyên. Mỗi bài toán có một thư mục con;
không tạo thêm `model/datasets/`.

## Cái gì nằm ở đây, cái gì vào git

**Thư mục này gần như toàn bộ bị gitignore.** Chỉ 3 loại file được version:

| File | Vì sao phải version |
|---|---|
| `README.md` (file này và của từng tập) | Mô tả cách dựng lại tập dữ liệu |
| `<tập>/dataset.lock.json` | Hash/label/split/group của snapshot đã làm sạch. Không chứa signed URL, secret hoặc PII trực tiếp |
| `../../data/knowledge/eval_set.json` | Tập vàng câu hỏi RAG — làm tay, mất là không dựng lại được |

**[NEVER] commit ảnh thật.** Ảnh cổng chứa biển số xe = PII. Chúng sống ở máy bạn hoặc bucket có kiểm soát; repo chỉ giữ file lock trỏ tới chúng.

## Các tập

| Tập | Dùng cho | Trạng thái |
|---|---|---|
| [`vehicle-cls/`](vehicle-cls/) | Phân loại loại xe (NetV1/NetV2) | ⬜ Chưa có ảnh |

Chỉ tạo `plate-detector/`, `plate-ocr/` hoặc `vehicle-reid/` khi phase tương ứng
bắt đầu và đã chốt schema nhãn. Không gom chúng vào `vehicle-cls/`: cùng là ảnh
nhưng target học hoàn toàn khác nhau.

## Dataset tải về (CIFAR, Animal-10)

Cũng nằm trong thư mục này và cũng bị gitignore, nhưng **[GOTCHA]** chúng chỉ để **kiểm kiến trúc mạng chạy được**, không phải để sinh ra model đưa vào dịch vụ. Ảnh web khác hoàn toàn ảnh camera cổng về góc máy, ánh sáng và độ nhoè — train trên đó rồi đem ra cổng là đổi bài toán giữa chừng (ADR-0003 §1).
