# core/vision/engines/anpr_engine.py
"""Engine nhận diện biển số xe — YOLO detection + EasyOCR.

Tất cả model (YOLO, EasyOCR reader) được lazy-load lần đầu tiên gọi ``run_anpr``
thay vì load ngay khi import, tránh block startup 5-10 giây khi chưa cần ANPR.
Entrypoint gRPC gọi ``warmup()`` để trả giá nạp model một lần lúc khởi động thay
vì bắt request thật đầu tiên chịu (xem ``app/grpc_server.py``).
"""
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import cv2
import numpy as np
import threading
import time
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from app.config import get_config
from app.core.constants import FALLBACK_PLATE_NUMBER, PLATE_MAX_LENGTH, PLATE_MIN_ALPHA
from app.core.exceptions import PlateRecognitionError, InvalidImageError, ModelNotLoadedError
from app.infra.model_registry import (
    ArtifactResolutionError,
    ModelArtifactSpec,
    get_model_artifact_registry,
)
from app.util.logger import logger

# ── Lazy-loaded state ─────────────────────────────────────────────────────────

_state: Dict[str, Any] = {
    "yolo_model": None,
    "ocr_reader": None,
    "initialized": False,
}

# Nạp model KHÔNG được chạy hai lần song song, và cờ `initialized` chỉ được bật
# SAU khi nạp xong. Bật trước (bản cũ) khiến request thứ hai đi tiếp với reader
# vẫn là None → FAILED_PRECONDITION ngay sau mỗi lần restart pod.
_load_lock = threading.Lock()


def _ensure_models_loaded() -> None:
    """Lazy-load YOLO và EasyOCR reader lần đầu tiên sử dụng (thread-safe)."""
    if _state["initialized"]:
        return

    with _load_lock:
        # Kiểm lại bên trong lock: thread thứ hai chờ ở đây xong thì model đã sẵn.
        if _state["initialized"]:
            return

        vision = get_config().vision
        import torch

        device_str = vision.device.lower()
        use_cuda = (device_str in ("cuda", "gpu") or device_str == "auto") and torch.cuda.is_available()
        device_name = "cuda" if use_cuda else "cpu"
        _state["device"] = device_name
        logger.info(f"ANPR Engine device selected: {device_name} (torch.cuda.is_available={torch.cuda.is_available()})")

        # ── EasyOCR ──
        try:
            import easyocr
            ocr_kwargs = {"gpu": use_cuda}
            if vision.ocr_model_storage_dir.strip():
                ocr_kwargs["model_storage_directory"] = vision.ocr_model_storage_dir
            _state["ocr_reader"] = easyocr.Reader(vision.ocr_language_list, **ocr_kwargs)
            logger.info(f"EasyOCR loaded: languages={vision.ocr_language_list}, gpu={use_cuda}")
        except Exception as exc:
            logger.error(f"Failed to load EasyOCR: {exc}")

        # ── YOLO ──
        try:
            model_path = get_model_artifact_registry().resolve(
                ModelArtifactSpec(
                    name="plate-detector",
                    version=vision.yolo_model_version,
                    file_name="best.pt",
                    local_path=vision.yolo_model_path,
                    source_url=vision.yolo_artifact_url,
                    sha256=vision.yolo_artifact_sha256,
                )
            )
            from ultralytics import YOLO
            yolo = YOLO(str(model_path))
            if use_cuda:
                try:
                    yolo.to("cuda")
                except Exception as exc:
                    logger.warning(f"Could not move YOLO model to CUDA: {exc}")
            _state["yolo_model"] = yolo
            logger.info(f"YOLO model loaded: {model_path} on {device_name}")
        except ArtifactResolutionError as exc:
            logger.warning(f"YOLO model artifact unavailable: {exc}")
        except Exception as exc:
            logger.error(f"Failed to load YOLO model: {exc}")

        _state["initialized"] = True


def warmup() -> bool:
    """Nạp sẵn model lúc khởi động. Trả về True khi OCR reader đã sẵn sàng.

    Gọi từ entrypoint: readiness probe xanh trong khi model chưa nạp là cách
    chắc chắn nhất để k8s bơm traffic vào một pod chưa phục vụ được.
    """
    _ensure_models_loaded()
    return _state["ocr_reader"] is not None


# ── Text processing ──────────────────────────────────────────────────────────

def sanitize_plate_text(text: str) -> str:
    text = text.upper()
    text = re.sub(r'[^A-Z0-9\-.]', '', text)
    return text


_DIGIT_TO_LETTER = {'0': 'D', '8': 'B', '5': 'S', '2': 'Z', '6': 'G', '4': 'A'}
_LETTER_TO_DIGIT = {'B': '8', 'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'A': '4', 'T': '7'}


def correct_vietnamese_plate(text: str) -> str:
    """Tự động hiệu chỉnh lỗi nhận dạng quang học dựa theo quy chuẩn biển số Việt Nam (TT 24/2023/TT-BCA).

    - Mã tỉnh (2 ký tự đầu): Bắt buộc là số (vd: 'B0' -> '30', 'B1' -> '51', 'O'/'D' -> '0').
    - Sê-ri xe con/xe tải: 1 chữ cái sau mã tỉnh (vd: '290' -> '29D', '308' -> '30B').
    - Dãy số đăng ký: Bắt buộc là các chữ số (vd: 'B' -> '8', 'O'/'D' -> '0').
    - Chuẩn hóa phân tách: 'XXY-ZZZ.ZZ' (ô tô) hoặc 'XX-YZ-ZZZ.ZZ' (xe máy).
    - Cắt lọc nhiễu ốc vít hoặc logo viền khung (vd: đuôi '-4' ở mép biển).
    """
    if not text:
        return text
    clean = re.sub(r'[^A-Z0-9\-.]', '', text.upper()).strip()
    if not clean:
        return ""

    chars = list(clean)
    # 1. Xử lý mã địa phương (2 ký tự đầu bắt buộc là chữ số)
    if len(chars) >= 2:
        if chars[0] == 'B' and chars[1] in '0123456789':
            chars[0] = '3' if chars[1] == '0' else '8'
        elif chars[0] in _LETTER_TO_DIGIT:
            chars[0] = _LETTER_TO_DIGIT[chars[0]]

        if chars[1] in _LETTER_TO_DIGIT:
            chars[1] = _LETTER_TO_DIGIT[chars[1]]

    cur = ''.join(chars)

    # 2. Định dạng ô tô: 2 số mã tỉnh, 1 sê-ri (chữ cái), dãy 4-5 số (vd: 30F-937.05, 51F-970.22, 290-012.45)
    m_auto = re.search(r'(\d{2})\-?([A-Z0-9])[\-.]?(\d{3,5}(?:[\-.]\d{2})?)', cur)
    if m_auto:
        prov, series, num = m_auto.groups()
        if series in _DIGIT_TO_LETTER:
            series = _DIGIT_TO_LETTER[series]
        clean_num = re.sub(r'[^0-9]', '', num)
        num_chars = [_LETTER_TO_DIGIT.get(c, c) for c in clean_num]
        clean_num = ''.join(num_chars)
        if len(clean_num) > 5:
            clean_num = clean_num[:5]
        if len(clean_num) == 5:
            num_fmt = f"{clean_num[:3]}.{clean_num[3:]}"
        else:
            num_fmt = clean_num
        return f"{prov}{series}-{num_fmt}"

    # 3. Định dạng xe máy: 2 số mã tỉnh, sê-ri 2 ký tự (chữ + số), dãy số (vd: 59-V1-793.79, 29-B1-123.45)
    m_moto = re.search(r'(\d{2})\-?([A-Z])([0-9A-Z])[\-.]?(\d{3,5}(?:[\-.]\d{2})?)', cur)
    if m_moto:
        prov, s1, s2, num = m_moto.groups()
        clean_num = re.sub(r'[^0-9]', '', num)
        num_chars = [_LETTER_TO_DIGIT.get(c, c) for c in clean_num]
        clean_num = ''.join(num_chars)
        if len(clean_num) > 5:
            clean_num = clean_num[:5]
        if len(clean_num) == 5:
            num_fmt = f"{clean_num[:3]}.{clean_num[3:]}"
        else:
            num_fmt = clean_num
        return f"{prov}-{s1}{s2}-{num_fmt}"

    return cur


def _is_valid_plate(text: str) -> bool:
    """Kiểm tra biển số hợp lệ: tối đa PLATE_MAX_LENGTH ký tự, ít nhất PLATE_MIN_ALPHA chữ cái."""
    return (
        len(text) <= PLATE_MAX_LENGTH
        and len(re.findall(r'[A-Z]', text)) >= PLATE_MIN_ALPHA
    )


def _plate_key(text: str) -> str:
    """Khoá dùng để so kết quả giữa các nhánh OCR.

    Dấu ``-``/``.`` thường biến mất sau resize hoặc threshold. Chúng vẫn được
    giữ trong kết quả trả về, nhưng không nên làm hai lần đọc cùng một biển bị
    xem là hai kết quả khác nhau.
    """
    return re.sub(r"[^A-Z0-9]", "", sanitize_plate_text(text))


@dataclass(frozen=True)
class _PlateCandidate:
    """Một giả thuyết biển số cùng bằng chứng tạo ra nó."""

    text: str
    ocr_confidence: float
    detector_confidence: Optional[float]
    source: str
    image: Any

    @property
    def key(self) -> str:
        return _plate_key(self.text)

    @property
    def confidence(self) -> float:
        return _combine_confidence(self.detector_confidence, self.ocr_confidence)


def _is_plausible_plate_shape(text: str) -> bool:
    """Điểm cộng mềm cho hình dạng thường gặp, không thay validation hiện tại."""
    key = _plate_key(text)
    digits = sum(char.isdigit() for char in key)
    letters = sum(char.isalpha() for char in key)
    return 7 <= len(key) <= 10 and digits >= 5 and letters >= PLATE_MIN_ALPHA


def _separator_evidence(text: str) -> int:
    """Số dấu phân cách OCR thật sự nhìn thấy, không tự suy diễn/chèn thêm."""
    return int("-" in text) + int("." in text)


def _has_strong_format_evidence(candidate: _PlateCandidate) -> bool:
    """Chỉ coi dấu là bằng chứng mạnh khi cả OCR lẫn detector đủ dùng."""
    detector_ok = (
        candidate.detector_confidence is None
        or candidate.detector_confidence >= 0.40
    )
    return (
        _separator_evidence(candidate.text) == 2
        and candidate.ocr_confidence >= 0.60
        and detector_ok
    )


def _select_plate_candidate(candidates: Iterable[_PlateCandidate]) -> Optional[_PlateCandidate]:
    """Chọn kết quả bằng đồng thuận + confidence, tuyệt đối không bằng độ dài.

    Lỗi thực tế đã gặp: dấu gạch ngang ``-`` trong crop bị EasyOCR đọc thành
    token ``7`` confidence thấp. Chuỗi sai dài hơn một ký tự nên thuật toán cũ
    chọn nó. Ở đây, hai nhánh cùng đọc ra một khoá sẽ thắng một kết quả
    dài nhưng chỉ xuất hiện một lần; khi chưa có đồng thuận thì ưu tiên hình
    dạng hợp lý và điểm tin cậy đo được.
    """
    valid = [
        candidate
        for candidate in candidates
        if candidate.text != FALLBACK_PLATE_NUMBER
        and _is_valid_plate(candidate.text)
        and candidate.key
    ]
    if not valid:
        return None

    support = Counter(candidate.key for candidate in valid)
    return max(
        valid,
        key=lambda candidate: (
            support[candidate.key],
            _is_plausible_plate_shape(candidate.text),
            _has_strong_format_evidence(candidate),
            candidate.confidence,
            candidate.ocr_confidence,
        ),
    )


# ── Core detection functions ──────────────────────────────────────────────────

def _read_with_confidence(img) -> Tuple[str, float]:
    """Đọc chữ + điểm tin cậy THẬT của EasyOCR.

    EasyOCR trả `(bbox, text, conf)` cho từng cụm chữ. Gộp điểm theo TRỌNG SỐ
    ĐỘ DÀI: một cụm 1 ký tự đọc chắc chắn không được kéo điểm của cả biển lên.
    Không đọc được cụm nào → 0.0, KHÔNG bịa số.
    """
    reader = _state["ocr_reader"]
    if reader is None:
        raise ModelNotLoadedError("EasyOCR reader chưa được load.")

    if isinstance(img, np.ndarray) and img.size > 0:
        h, w = img.shape[:2]
        max_dim = max(h, w)
        if max_dim > 640:
            scale = 640.0 / max_dim
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    results = reader.readtext(img)
    if not results:
        return "", 0.0

    # Sắp xếp các cụm chữ theo thứ tự từ trên xuống dưới (Y), sau đó từ trái sang phải (X)
    # Lưu ý: trong unit test mock, bbox (res[0]) có thể là None
    has_valid_boxes = all(
        res[0] is not None and isinstance(res[0], (list, tuple)) and len(res[0]) > 0 and len(res[0][0]) > 1
        for res in results
    )
    sorted_res = sorted(results, key=lambda r: (r[0][0][1], r[0][0][0])) if has_valid_boxes else results

    parts = []
    for i, res in enumerate(sorted_res):
        text = res[1].strip()
        if not text:
            continue
        # Khắc phục lỗi OCR đọc nhầm ký tự gạch chéo thay cho chữ cái (ví dụ / thay cho V)
        if '/' in text:
            text = text.replace('/', 'V')
        if i > 0 and parts and has_valid_boxes:
            prev_y = sorted_res[i - 1][0][0][1]
            curr_y = res[0][0][1]
            # Nếu 2 cụm chữ nằm ở 2 dòng khác nhau (khoảng cách Y đáng kể)
            if abs(curr_y - prev_y) > 20 and not parts[-1].endswith(('-', '.')) and not text.startswith(('-', '.')):
                parts.append('-')
        parts.append(text)

    text_raw = ''.join(parts)
    total_chars = sum(len(res[1]) for res in sorted_res)
    if total_chars == 0:
        return sanitize_plate_text(text_raw), 0.0

    weighted = sum(float(res[2]) * len(res[1]) for res in sorted_res)
    return sanitize_plate_text(text_raw), weighted / total_chars


def get_plate_text_from_image(img) -> Tuple[str, float]:
    """Trả `(biển số đã chuẩn hoá, điểm tin cậy OCR)`."""
    return _read_with_confidence(img)


def detect_plate_yolo(img_cv) -> Tuple[Any, Optional[float]]:
    """Trả `(ảnh crop, điểm tin cậy của box)`.

    `None` ở vị trí điểm nghĩa là KHÔNG có detector (chưa nạp được YOLO).
    Tự động giải phóng GPU memory và fallback CPU nếu gặp CUDA OOM.
    """
    model = _state["yolo_model"]
    if model is None:
        return img_cv, None
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    device = _state.get("device", "cpu")
    try:
        results = model(img_rgb, device=device)
    except TypeError:
        # Hỗ trợ mock hoặc model không nhận keyword argument `device` (như _FakeYolo trong unit test)
        results = model(img_rgb)
    except Exception as exc:
        if "out of memory" in str(exc).lower() or "cuda" in str(exc).lower():
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
            results = model(img_rgb, device="cpu")
        else:
            raise

    boxes = results[0].boxes
    xyxy = boxes.xyxy.cpu().numpy()
    if len(xyxy) == 0:
        raise PlateRecognitionError("Không phát hiện được biển số")

    confidences = boxes.conf.cpu().numpy() if boxes.conf is not None else None
    height, width = img_cv.shape[:2]

    # Gộp các box chồng lấn (khi YOLO phát hiện 2 nửa của cùng một biển số dài)
    if len(xyxy) > 1 and confidences is not None:
        conf_arr = np.asarray(confidences, dtype=float)
        max_c = float(np.max(conf_arr))
        keep_indices = [i for i, c in enumerate(conf_arr) if c >= min(0.25, max_c * 0.5)]
        if not keep_indices:
            keep_indices = [int(np.argmax(conf_arr))]

        kboxes = xyxy[keep_indices]
        kconf = conf_arr[keep_indices]

        groups = []
        used = set()
        for i in range(len(kboxes)):
            if i in used:
                continue
            bx1, by1, bx2, by2 = kboxes[i]
            bconf = float(kconf[i])
            for j in range(i + 1, len(kboxes)):
                if j in used:
                    continue
                jx1, jy1, jx2, jy2 = kboxes[j]
                v_inter = min(by2, jy2) - max(by1, jy1)
                v_min = min(by2 - by1, jy2 - jy1)
                v_overlap = v_inter / max(1.0, v_min)
                h_inter = min(bx2, jx2) - max(bx1, jx1)
                # Giao thoa trục Y và gần kề hoặc chồng lấn trục X
                if v_overlap > 0.40 and h_inter > -30:
                    bx1 = min(bx1, jx1)
                    by1 = min(by1, jy1)
                    bx2 = max(bx2, jx2)
                    by2 = max(by2, jy2)
                    bconf = max(bconf, float(kconf[j]))
                    used.add(j)
            groups.append(((int(bx1), int(by1), int(bx2), int(by2)), bconf))
            used.add(i)

        best_box, det_conf = max(groups, key=lambda x: x[1])
        x1, y1, x2, y2 = best_box
    else:
        best_index = int(np.argmax(confidences)) if confidences is not None else 0
        x1, y1, x2, y2 = xyxy[best_index].astype(int)
        det_conf = float(confidences[best_index]) if confidences is not None else None

    # Thêm lề đệm an toàn (padding 6% ngang, 8% dọc) để không cắt phạm vào ký tự đầu/cuối
    bw = x2 - x1
    bh = y2 - y1
    pad_w = int(0.06 * bw)
    pad_h = int(0.08 * bh)
    x1 = max(0, x1 - pad_w)
    y1 = max(0, y1 - pad_h)
    x2 = min(width, x2 + pad_w)
    y2 = min(height, y2 + pad_h)

    if x2 <= x1 or y2 <= y1:
        raise PlateRecognitionError("Vùng biển số detector trả về không hợp lệ")

    crop = img_cv[y1:y2, x1:x2]
    return crop, det_conf


def detect_plate_color(crop: np.ndarray) -> str:
    """Xác định màu nền biển số xe theo quy chuẩn Việt Nam (white, yellow, blue, red).

    Phân tích không gian màu HSV trên các pixel nền trung tâm (loại trừ pixel chữ tối màu).
    Mặc định dân sự là 'white', chỉ kết luận màu khác khi tỷ lệ màu chuyên dụng áp đảo (>= 35%).
    """
    if not isinstance(crop, np.ndarray) or crop.size == 0:
        return "white"

    # Lấy vùng trung tâm biển số để tránh dính màu sơn thân vỏ xe ở mép ngoài
    h, w = crop.shape[:2]
    if h >= 30 and w >= 50:
        sample = crop[int(h * 0.15):int(h * 0.85), int(w * 0.15):int(w * 0.85)]
    else:
        sample = crop

    hsv = cv2.cvtColor(sample, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = cv2.split(hsv)

    # Loại bỏ các pixel chữ quá tối (V < 60)
    bg_mask = v_ch >= 60
    total_bg = np.count_nonzero(bg_mask)
    if total_bg == 0:
        return "white"

    # Màu vàng (Yellow - kinh doanh vận tải): Hue 15-38, Saturation >= 60, Value >= 75
    yellow_mask = (h_ch >= 15) & (h_ch <= 38) & (s_ch >= 60) & (v_ch >= 75) & bg_mask
    yellow_ratio = np.count_nonzero(yellow_mask) / total_bg

    # Màu xanh (Blue - cơ quan công quyền): Hue 95-130, Saturation >= 70, Value >= 60
    blue_mask = (h_ch >= 95) & (h_ch <= 130) & (s_ch >= 70) & (v_ch >= 60) & bg_mask
    blue_ratio = np.count_nonzero(blue_mask) / total_bg

    # Màu đỏ (Red - quân đội): Hue <= 10 hoặc >= 170, Saturation >= 75
    red_mask = ((h_ch <= 10) | (h_ch >= 170)) & (s_ch >= 75) & (v_ch >= 60) & bg_mask
    red_ratio = np.count_nonzero(red_mask) / total_bg

    if yellow_ratio >= 0.35 and yellow_ratio > blue_ratio and yellow_ratio > red_ratio:
        return "yellow"
    if blue_ratio >= 0.35 and blue_ratio > yellow_ratio and blue_ratio > red_ratio:
        return "blue"
    if red_ratio >= 0.35 and red_ratio > yellow_ratio and red_ratio > blue_ratio:
        return "red"
    return "white"


def enhance_yellow_plate(crop: np.ndarray) -> np.ndarray:
    """Tối ưu độ tương phản cho biển số màu vàng bằng phép tách kênh (R - B).

    Biển vàng có kênh R cao, G cao, B thấp. Ký tự đen có R, G, B đều thấp.
    Hiệu (R - B) triệt tiêu hoàn toàn nhiễu nền và cho độ tương phản ký tự tối đa.
    """
    if not isinstance(crop, np.ndarray) or crop.size == 0:
        return crop
    b, g, r = cv2.split(crop)
    diff = cv2.subtract(r, b)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(norm)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def deskew_plate(crop: np.ndarray) -> np.ndarray:
    """Cân chỉnh góc nghiêng (deskewing) cho biển số bị chụp xéo góc (2° - 35°)."""
    if not isinstance(crop, np.ndarray) or crop.shape[0] < 20 or crop.shape[1] < 40:
        return crop

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return crop

    h, w = crop.shape[:2]
    img_area = w * h

    best_cnt = None
    max_area = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > max_area and area > 0.12 * img_area:
            max_area = area
            best_cnt = cnt

    if best_cnt is None:
        return crop

    rect = cv2.minAreaRect(best_cnt)
    (cx, cy), (rw, rh), angle = rect

    if rw < rh:
        angle = angle + 90.0
    if angle > 45.0:
        angle -= 90.0
    elif angle < -45.0:
        angle += 90.0

    if 2.0 <= abs(angle) <= 35.0:
        center = (w / 2.0, h / 2.0)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            crop, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated

    return crop


def enhanced_ocr(plate_crop):
    h, w = plate_crop.shape[:2]

    # Xử lý đặc thù cho biển số vuông 2 dòng (xe máy, tỷ lệ w/h < 2.0)
    if (w / h) < 2.0 and h >= 50:
        line1_crop = plate_crop[:int(h * 0.52), :]
        line2_crop = plate_crop[int(h * 0.45):, :]

        # Tiền xử lý Otsu binarization trên Line 1 (làm sạch viền dập nổi và quốc huy)
        gray1 = cv2.cvtColor(line1_crop, cv2.COLOR_BGR2GRAY)
        _, otsu1 = cv2.threshold(gray1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        t1, conf1 = _read_with_confidence(otsu1)

        # Đọc Line 2
        t2, conf2 = _read_with_confidence(line2_crop)

        if t1 and t2:
            t1_clean = t1.replace('/', 'V').replace('|', '1').strip('-')
            t2_clean = t2.strip('-')
            combined = f"{t1_clean}-{t2_clean}"
            combined_sanitized = sanitize_plate_text(combined)
            if _is_valid_plate(combined_sanitized):
                avg_conf = (conf1 + conf2) / 2.0
                return combined_sanitized, plate_crop, avg_conf

    # Nếu là biển vàng, áp dụng tách kênh R - B
    color = detect_plate_color(plate_crop)
    if color == "yellow":
        yellow_enh = enhance_yellow_plate(plate_crop)
        t_y, conf_y = _read_with_confidence(yellow_enh)
        if _is_valid_plate(t_y):
            return t_y, yellow_enh, conf_y

    if w < 100 or h < 80:
        scale_w = 150 / w if w > 0 else 2.0
        scale_h = 100 / h if h > 0 else 2.0
        scale_factor = max(scale_w, scale_h, 2.0)
        plate_crop = cv2.resize(plate_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)

    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, d=7, sigmaColor=60, sigmaSpace=60)
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    contrast = clahe.apply(filtered)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(contrast, -1, kernel)

    min_val, max_val = np.min(sharpened), np.max(sharpened)
    if max_val == min_val:
        stretched = sharpened
    else:
        stretched = ((sharpened - min_val) / (max_val - min_val) * 255).astype(np.uint8)

    plate_text, ocr_conf = _read_with_confidence(stretched)
    return plate_text, stretched, ocr_conf


def is_valid_crop(crop_img, min_w=50, min_h=30, min_brightness=30) -> bool:
    if not isinstance(crop_img, np.ndarray):
        return False
    h, w = crop_img.shape[:2]
    if w < min_w or h < min_h:
        return False
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    return np.mean(gray) >= min_brightness


def _combine_confidence(det_conf: Optional[float], ocr_conf: float) -> float:
    """Ghép điểm detector và điểm OCR thành một điểm cho cả lượt nhận diện.

    Nhân hai điểm chứ không lấy trung bình: đọc chữ rất chắc trên một vùng ảnh
    mà detector chỉ 30% tin là biển số thì cả lượt vẫn phải đáng ngờ.
    `det_conf is None` = không có detector → điểm cuối chính là điểm OCR.
    """
    if det_conf is None:
        return ocr_conf
    return det_conf * ocr_conf


# ── Public API ────────────────────────────────────────────────────────────────

def run_anpr(ori_bytes: bytes) -> Dict[str, Any]:
    """Chạy full pipeline ANPR trên raw bytes ảnh.

    Returns:
        dict với keys: ``crop_bytes``, ``plate_number``, ``confidence``,
        ``process_time``, ``plate_color``.
    """
    _ensure_models_loaded()

    if not ori_bytes:
        raise InvalidImageError("Ảnh đầu vào rỗng.")

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass

    start_time = time.time()
    npimg = np.frombuffer(ori_bytes, np.uint8)
    img_cv = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise InvalidImageError("Không thể decode ảnh đầu vào.")

    candidates = []
    crop_text = ""
    crop_conf = 0.0
    det_conf = None
    plate_crop = None
    crop_is_valid = False
    yolo_failed = False
    detected_color = "white"

    try:
        # 1. Phát hiện biển số bằng YOLO trước (chạy siêu tốc trên GPU)
        try:
            plate_crop, det_conf = detect_plate_yolo(img_cv)
            if isinstance(plate_crop, np.ndarray) and not (
                det_conf is None and plate_crop is img_cv
            ):
                # Cân chỉnh góc nghiêng (deskew)
                plate_crop = deskew_plate(plate_crop)
                detected_color = detect_plate_color(plate_crop)

                # Smart Scale: Tinh chỉnh tỷ lệ để ký tự đạt độ cao tối ưu (35-50px) cho CRNN
                ch, cw = plate_crop.shape[:2]
                ocr_input = plate_crop
                if 0 < ch < 180:
                    scale = min(2.0, 200.0 / ch)
                    if scale > 1.1:
                        ocr_input = cv2.resize(plate_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

                crop_is_valid = is_valid_crop(plate_crop)
                if crop_is_valid:
                    crop_text, crop_conf = get_plate_text_from_image(ocr_input)
                    if _is_valid_plate(crop_text):
                        candidates.append(
                            _PlateCandidate(crop_text, crop_conf, det_conf, "crop", plate_crop)
                        )
                    corr_text = correct_vietnamese_plate(crop_text)
                    if corr_text != crop_text and _is_valid_plate(corr_text):
                        candidates.append(
                            _PlateCandidate(corr_text, crop_conf, det_conf, "crop_corrected", plate_crop)
                        )

                # Thử thêm nhánh biển số vàng nếu nhận diện nền vàng
                if detected_color == "yellow":
                    try:
                        y_crop = enhance_yellow_plate(ocr_input)
                        y_text, y_conf = get_plate_text_from_image(y_crop)
                        if _is_valid_plate(y_text):
                            candidates.append(
                                _PlateCandidate(y_text, y_conf, det_conf, "yellow_contrast", y_crop)
                            )
                        corr_y = correct_vietnamese_plate(y_text)
                        if corr_y != y_text and _is_valid_plate(corr_y):
                            candidates.append(
                                _PlateCandidate(corr_y, y_conf, det_conf, "yellow_corrected", y_crop)
                            )
                    except Exception as exc:
                        logger.warning(f"Yellow plate enhancement error: {exc}")
            else:
                yolo_failed = True
        except PlateRecognitionError:
            yolo_failed = True
        except Exception as exc:
            logger.warning(f"YOLO detection error (non-fatal): {exc}")
            yolo_failed = True

        crop_key = _plate_key(crop_text) if _is_valid_plate(crop_text) else ""

        has_crop = plate_crop is not None and isinstance(plate_crop, np.ndarray) and plate_crop is not img_cv

        # 2. Enhance OCR: chạy khi có crop và chưa có candidate đủ mạnh
        if has_crop:
            try:
                enhanced_text, enhanced_img, enhanced_conf = enhanced_ocr(plate_crop)
                if _is_valid_plate(enhanced_text):
                    candidates.append(
                        _PlateCandidate(
                            enhanced_text,
                            enhanced_conf,
                            det_conf,
                            "enhanced",
                            enhanced_img,
                        )
                    )
                corr_enh = correct_vietnamese_plate(enhanced_text)
                if corr_enh != enhanced_text and _is_valid_plate(corr_enh):
                    candidates.append(
                        _PlateCandidate(
                            corr_enh,
                            enhanced_conf,
                            det_conf,
                            "enhanced_corrected",
                            enhanced_img,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Enhanced OCR error: {exc}")

        # 3. Quét toàn khung (full frame) CHỈ KHI detector không tìm được crop (plate_crop is None)
        # Tuyệt đối không quét full-frame nếu đã có crop vì sẽ tốn VRAM và dễ đọc nhầm biển hiệu nền.
        if not has_crop and (yolo_failed or not candidates):
            try:
                full_text, full_conf = get_plate_text_from_image(img_cv)
                if _is_valid_plate(full_text):
                    candidates.append(
                        _PlateCandidate(full_text, full_conf, None, "full", img_cv)
                    )
                corr_full = correct_vietnamese_plate(full_text)
                if corr_full != full_text and _is_valid_plate(corr_full):
                    candidates.append(
                        _PlateCandidate(corr_full, full_conf, None, "full_corrected", img_cv)
                    )
            except Exception as exc:
                logger.warning(f"Full-frame OCR fallback error: {exc}")

        selected = _select_plate_candidate(candidates)
        if selected is None:
            plate_number = FALLBACK_PLATE_NUMBER
            plate_confidence = 0.0
            processed_image = plate_crop if has_crop else img_cv
        else:
            plate_number = correct_vietnamese_plate(selected.text)
            plate_confidence = selected.confidence
            processed_image = selected.image

        success, buffer = cv2.imencode('.jpg', processed_image)
        if not success:
            raise PlateRecognitionError("Chuyển ảnh crop sang bytes thất bại.")

        crop_bytes = buffer.tobytes()
        process_time = round(time.time() - start_time, 3)

        return {
            "crop_bytes": crop_bytes,
            "plate_number": plate_number,
            "confidence": round(plate_confidence, 4),
            "process_time": process_time,
            "plate_color": detected_color,
        }
    finally:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
