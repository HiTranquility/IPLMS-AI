# IPLMS AI — ANPR + Copilot + Forecast (FastAPI REST :8000 & gRPC :50051, CPU).
#
# ⚠️ BUILD CONTEXT LÀ GỐC REPO, không phải thư mục ai/:
#     docker build -f ai/Dockerfile -t iplms-ai:latest .
# Lý do: hợp đồng `proto/` nằm ở gốc repo và dùng chung với backend. Đặt context
# ở ai/ thì proto nằm ngoài tầm COPY, buộc phải nhân bản proto — đúng thứ gây
# lệch hợp đồng giữa hai phía.
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libs OpenCV / torch / easyocr cần lúc chạy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY ai/requirements-service.txt .
RUN pip install -r requirements-service.txt

# model/ chứa kiến trúc, bootstrap YOLO và workspace train; image chỉ cần model.
COPY ai/app ./app
COPY ai/model ./model
COPY ai/static ./static
COPY proto ./proto

# Sinh stub gRPC ngay lúc build — nếu thiếu, server sẽ chết ở entrypoint chứ
# không phải giữa một request nhận diện.
RUN python app/script/compile_proto.py

# Nướng sẵn model EasyOCR (~113MB) vào image. Nếu không, chúng được tải về lúc
# xử lý ẢNH ĐẦU TIÊN: pod restart là tải lại, và cụm không có Internet (kịch bản
# bảo vệ offline) thì ANPR chết hẳn. Đổi lại image nặng thêm ~113MB.
#
# CỐ Ý không để bước này phá build: máy build không có mạng thì vẫn ra được image,
# chỉ là quay về hành vi cũ (tải lúc chạy). Đọc dòng cảnh báo trong log build để
# biết image có tự chứa model hay không.
RUN python -c "import easyocr, os; easyocr.Reader(os.getenv('AI_OCR_LANGUAGES','en,vi').split(','), gpu=False)" \
      && echo "Model EasyOCR da nam san trong image." \
      || echo "CANH BAO: khong tai duoc model EasyOCR luc build - se tai o request ANPR dau tien (can Internet luc chay)."

COPY ai/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000 50051
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
