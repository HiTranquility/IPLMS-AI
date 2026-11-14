# IPLMS AI — ANPR + Copilot + Forecast (FastAPI REST :8000 & gRPC :50051, CPU).
#
# Build context là CHÍNH THƯ MỤC NÀY (repo IPLMS-AI), không cần repo cha:
#     docker build -t iplms-ai:latest .
# Hợp đồng gRPC lấy từ `proto/` của repo này — bản chép từ `IPLMS/proto/` (nguồn
# chuẩn), được `IPLMS/proto/check_proto_sync.py` canh lệch. Xem ADR-0006.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ONNXRUNTIME_EXECUTION_PROVIDERS=CPUExecutionProvider

WORKDIR /app

# System libs OpenCV / torch / easyocr cần lúc chạy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-service.txt .
RUN pip install -r requirements-service.txt

# model/ chứa kiến trúc, bootstrap YOLO và workspace train; data/ chứa dữ liệu và ONNX models.
COPY app ./app
COPY model ./model
COPY static ./static
COPY data ./data
COPY proto ./proto

# Đảm bảo các thư mục model và data ONNX tồn tại và gán quyền phù hợp
RUN mkdir -p /app/data/models /app/model/artifacts /app/var/model-cache \
    && chmod -R 755 /app/model /app/data /app/var

# Sinh stub gRPC và xuất sẵn trọng số ANPR ONNX ngay lúc build — nếu hỏng, build
# dừng sớm thay vì âm thầm rơi về PyTorch chậm lúc chạy.
RUN python app/script/compile_proto.py \
    && python app/script/export_anpr_onnx.py

# Nướng sẵn model EasyOCR (~113MB) vào image. Nếu không, chúng được tải về lúc
# xử lý ẢNH ĐẦU TIÊN: pod restart là tải lại, và cụm không có Internet (kịch bản
# bảo vệ offline) thì ANPR chết hẳn. Đổi lại image nặng thêm ~113MB.
#
# CỐ Ý không để bước này phá build: máy build không có mạng thì vẫn ra được image,
# chỉ là quay về hành vi cũ (tải lúc chạy). Đọc dòng cảnh báo trong log build để
# biết image có tự chứa model hay không.
ARG PRELOAD_EASYOCR_MODELS=true
RUN if [ "$PRELOAD_EASYOCR_MODELS" = "true" ]; then \
      python -c "import easyocr, os; easyocr.Reader(os.getenv('AI_OCR_LANGUAGES','en,vi').split(','), gpu=False)" \
        && echo "Model EasyOCR da nam san trong image." \
        || echo "CANH BAO: khong tai duoc model EasyOCR luc build - se tai o request ANPR dau tien (can Internet luc chay)."; \
    else \
      echo "Bo qua preload EasyOCR cho image dev; model se tai khi ANPR duoc goi lan dau."; \
    fi

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000 50051
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
