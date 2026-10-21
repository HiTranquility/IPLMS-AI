# Hướng dẫn cấu hình Checkpoint cho BTImages.py

Tài liệu này ghi lại các thay đổi đã được thực hiện trong `BTImages.py` để hỗ trợ tạo đúng thư mục lưu trữ checkpoints (dành cho các dataset như Cifar10, Cifar100 và theo kích thước ảnh như 32x32 hoặc 224x224).

---

## 1. Các tham số dòng lệnh mới được thêm vào

Ba tham số mới được thêm vào `argparse` để bạn có thể linh hoạt cấu hình:
- `--dataset` (Mặc định: `'cifar10'`): Tên dataset bạn sử dụng (ví dụ: `cifar10`, `cifar100`). Code sẽ tự động phân giải cấu hình số lớp (`10` hoặc `100` classes) tương ứng.
- `--img-size` (Mặc định: `32`): Kích thước ảnh được dùng trong mô hình (ví dụ: `32` cho Cifar, `224` cho kích thước thông thường).
- `--net` (Mặc định: `'NetV1'`): Tên của kiến trúc mạng bạn muốn mô hình khởi tạo (ví dụ: `NetV1`).

**Ví dụ khi chạy code:**
```bash
python BTImages.py --dataset cifar10 --img-size 32 --net NetV1 --epochs 100
python BTImages.py --dataset cifar100 --img-size 224 --net NetV1 --epochs 100
```

---

## 2. Cấu trúc thư mục Checkpoints

Thư mục tự động tạo ra giờ đây sẽ được định dạng quy chuẩn để bạn dễ dàng quản lý:
`./model/checkpoint/<dataset>_<img_size>x<img_size>_<arch>_<action>/`

**Ví dụ thực tế:**
- Nếu bạn chạy `--dataset cifar10 --img-size 32 --net NetBT2`:
  Thư mục sinh ra: `./model/checkpoint/cifar10_32x32_BTImages10_NetBT2/`
- Nếu bạn chạy `--dataset cifar100 --img-size 224 --net NetV1` (với `--action exp1`):
  Thư mục sinh ra: `./model/checkpoint/cifar100_224x224_BTImages100_NetV1_exp1/`

---

## 3. Các thay đổi bên trong Code (Tóm tắt)

1. **Parser & Params:** Thêm `--dataset`, `--img-size` và `--net` ở phần khai báo tham số.
2. **Main:** 
   - Thay đoạn fix cứng số lớp `n_class = 30` bằng lệnh if-else kiểm tra `args.dataset`.
   - Thay vì khởi tạo class `NetBT2` mặc định, mô hình sẽ được gọi từ `globals()[args.net]` để gán class một cách tự động theo tham số bạn truyền vào đường dẫn lệnh.
3. **Định nghĩa thư mục:** Tạo thuộc tính động `args.checkpoint_dir`.
4. **Cập nhật đường dẫn:** Chỉnh sửa tất cả những chỗ xử lý checkpoint bao gồm: log txt, file checkpoint best epoch, và chỗ gọi lưu checkpoint `save_checkpoint` để trỏ vào `args.checkpoint_dir`.

*Lưu ý: Quá trình transform ảnh (như Resize hay RandomCrop) vẫn giữ nguyên theo framework gốc ở phía dưới để không bị thay đổi logic của module dataset đã có, chúng ta chỉ thay đổi thư mục lưu checkpoints như được yêu cầu.*
