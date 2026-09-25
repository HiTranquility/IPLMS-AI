import os

# Thư mục chứa file này: ai/app/util
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# STATIC_ROOT = ai/static  (app/ và static/ là anh em dưới ai/)
STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "static"))


def save_bytes_image(image_bytes: bytes, file_path: str) -> None:
    """Lưu ảnh vào ai/static/... đúng thư mục thực tế.
    file_path thường là '/static/original/abc.jpg' hoặc '/static/cropped/...'."""
    if file_path.startswith("/static/"):
        file_path = file_path[len("/static/"):]

    full_path = os.path.join(STATIC_ROOT, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, "wb") as f:
        f.write(image_bytes)
