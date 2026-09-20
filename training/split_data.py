import os
import random
import shutil

# Đường dẫn thư mục
source_dir = './model/dataset/Animal-10/raw-img'
train_dir = './model/dataset/Animal-10/train'
val_dir = './model/dataset/Animal-10/val'
test_dir = './model/dataset/Animal-10/test'  # NEW: Test set độc lập

# Tỷ lệ chia: 70% Train, 10% Val, 20% Test
train_ratio = 0.7
val_ratio = 0.1
test_ratio = 0.2


def split_dataset():
    print("🚀 Bắt đầu chia dataset...")

    # Tạo thư mục gốc nếu chưa có
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)  # NEW: Tạo test dir

    # Lấy danh sách các class (cane, cavallo,...)
    if not os.path.exists(source_dir):
        print(f"❌ Lỗi: Không tìm thấy thư mục {source_dir}")
        return

    classes = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]

    for cls in classes:
        cls_source_dir = os.path.join(source_dir, cls)
        cls_train_dir = os.path.join(train_dir, cls)
        cls_val_dir = os.path.join(val_dir, cls)
        cls_test_dir = os.path.join(test_dir, cls)  # NEW: Test dir cho class

        # Tạo thư mục cho từng class trong train, val và test
        os.makedirs(cls_train_dir, exist_ok=True)
        os.makedirs(cls_val_dir, exist_ok=True)
        os.makedirs(cls_test_dir, exist_ok=True)  # NEW: Tạo test dir

        # Lấy tất cả ảnh
        images = [f for f in os.listdir(cls_source_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        # Trộn ngẫu nhiên
        random.seed(42)  # Cố định seed để nếu lỡ chạy lại vẫn ra kết quả như cũ
        random.shuffle(images)

        # Cắt file: 70% train, 10% val, 20% test
        train_split = int(len(images) * train_ratio)
        val_split = train_split + int(len(images) * val_ratio)
        
        train_images = images[:train_split]
        val_images = images[train_split:val_split]
        test_images = images[val_split:]  # NEW: Test images

        # Copy file
        for img in train_images:
            shutil.copy(os.path.join(cls_source_dir, img), os.path.join(cls_train_dir, img))
        for img in val_images:
            shutil.copy(os.path.join(cls_source_dir, img), os.path.join(cls_val_dir, img))
        for img in test_images:  # NEW: Copy test images
            shutil.copy(os.path.join(cls_source_dir, img), os.path.join(cls_test_dir, img))

        print(f"✅ Class '{cls}': {len(train_images)} train | {len(val_images)} val | {len(test_images)} test")

    print("\n🎉 Hoàn thành! Đã chia xong dataset. Giờ bạn có thể chạy file train.")


if __name__ == '__main__':
    split_dataset()
