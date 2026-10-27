"""Các tầng của ANPR — mỗi module một lý do để thay đổi.

    models      nạp YOLO + EasyOCR (lazy, thread-safe), warm-up
    detector    YOLO tìm vùng biển số → ảnh cắt + điểm detector
    preprocess  ảnh cắt đủ tốt chưa? + làm nét/tăng tương phản trước khi OCR lại
    ocr         EasyOCR đọc chữ + điểm tin cậy thật (trọng số độ dài)
    plate_text  luật chuỗi biển số Việt Nam (chuẩn hoá, hợp lệ, khoá so sánh)
    scoring     ghép điểm detector × OCR, chọn ứng viên bằng đồng thuận
    two_line_plate_parser  ghép biển hai dòng
    onnx_engine            nhánh ONNX Runtime

`engine.run_anpr` là façade phối hợp các tầng này.
"""
