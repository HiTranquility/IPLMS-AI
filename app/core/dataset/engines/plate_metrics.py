"""Thước đo độ chính xác đọc biển số — hàm THUẦN, không nạp model.

Tách khỏi `eval_plates.py` có chủ đích: chỗ này không import `cv2`, `torch` hay
engine nào, nên `test/` import được và chạy trong vài mili-giây (đúng luật bộ
test ở `test/__init__.py`).

## Vì sao đo HAI kiểu exact-match

Biển thật là `51F-178.12`. OCR hiện tại đọc ra `51F17812` — đúng từng ký tự,
chỉ thiếu dấu phân cách. Nếu chỉ đo một kiểu:

- Chỉ đo **strict** ⇒ con số tệ một cách oan uổng, và không phân biệt được
  "đọc sai chữ" với "đọc đúng nhưng thiếu gạch".
- Chỉ đo **relaxed** ⇒ giấu mất đúng cái lỗi đang làm backend tra không ra xe:
  `vehicle.licensePlate = :trimmedPlate` so khớp CHUỖI CHÍNH XÁC, nên thiếu
  gạch là thành viên bị tính như khách vãng lai (xem `test/test_plate_text.py`).

Nên báo cáo cả hai. Khoảng cách giữa hai số chính là phần việc B2 (hậu xử lý
định dạng biển VN) sẽ lấy về — và là cách duy nhất chứng minh B2 đáng làm.
"""
from typing import Dict, Iterable, List, Optional, Sequence

# Ký tự chỉ đóng vai phân cách trong biển số VN. Bỏ chúng đi = so kiểu "relaxed".
PLATE_SEPARATORS = "-. "


def normalize_strict(plate: Optional[str]) -> str:
    """Viết hoa + cắt khoảng trắng hai đầu. GIỮ nguyên gạch ngang và dấu chấm."""
    return (plate or "").strip().upper()


def normalize_relaxed(plate: Optional[str]) -> str:
    """Như `normalize_strict` nhưng bỏ hết dấu phân cách."""
    text = normalize_strict(plate)
    for ch in PLATE_SEPARATORS:
        text = text.replace(ch, "")
    return text


def levenshtein(a: str, b: str) -> int:
    """Khoảng cách sửa (chèn/xoá/thay) giữa hai chuỗi.

    Cài tay bằng quy hoạch động 2 hàng thay vì kéo thêm một thư viện: biển số
    dài tối đa ~11 ký tự, chi phí không đáng kể, và bộ test phải chạy được
    ngay sau `pip install -r requirements.txt` mà không thêm dependency nào.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, ch_a in enumerate(a, start=1):
        current = [i]
        for j, ch_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,           # xoá
                    current[j - 1] + 1,        # chèn
                    previous[j - 1] + (ch_a != ch_b),  # thay
                )
            )
        previous = current
    return previous[-1]


def char_error_rate(truth: str, predicted: str) -> float:
    """CER = khoảng cách sửa / độ dài nhãn thật.

    Đo trên chuỗi **relaxed**: CER dùng để trả lời "đọc sai bao nhiêu ký tự",
    còn chuyện thiếu gạch đã có `exact_match_strict` chịu trách nhiệm. Trộn hai
    câu hỏi vào một con số thì không sửa được cái nào.

    Nhãn thật rỗng là lỗi dữ liệu, không phải kết quả đo — trả `1.0` khi đoán
    ra chữ, `0.0` khi cả hai cùng rỗng. CER có thể **lớn hơn 1** khi chuỗi đoán
    dài hơn nhãn; cố ý không cắt trần để một kết quả rác trông đúng như rác.
    """
    t = normalize_relaxed(truth)
    p = normalize_relaxed(predicted)
    if not t:
        return 0.0 if not p else 1.0
    return levenshtein(t, p) / len(t)


def percentile(values: Sequence[float], q: float) -> float:
    """Phân vị kiểu "nearest-rank" trên danh sách đã cho (tự sắp xếp).

    Không dùng `statistics.quantiles`: nó nội suy và cần >= 2 phần tử, trong khi
    ta hay đo trên tập vài chục ảnh và muốn p95 là **một lần chạy có thật**.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    if q <= 0:
        return ordered[0]
    rank = max(1, min(len(ordered), int(-(-q * len(ordered) // 1))))
    return ordered[rank - 1]


def score_one(truth: str, predicted: Optional[str]) -> Dict[str, object]:
    """Chấm MỘT ảnh. `predicted=None` nghĩa là pipeline không trả ra biển nào."""
    pred = predicted or ""
    return {
        "truth": normalize_strict(truth),
        "predicted": normalize_strict(pred),
        "exact_strict": normalize_strict(truth) == normalize_strict(pred),
        "exact_relaxed": normalize_relaxed(truth) == normalize_relaxed(pred)
        and bool(normalize_relaxed(truth)),
        "cer": char_error_rate(truth, pred),
    }


def aggregate(rows: Iterable[Dict[str, object]]) -> Dict[str, object]:
    """Gộp kết quả từng ảnh thành bảng số của cả lượt chạy.

    `rows` là các dict do `score_one` sinh ra, mỗi cái có thể kèm thêm
    `confidence`, `process_time`, `error`, `tags`.

    **`recognized` khác `exact`**: một lượt trả ra `UNKNOWN` hoặc ném lỗi vẫn là
    một lượt *đã chạy*. Tính nó vào mẫu số (chứ không bỏ qua) mới thấy được
    đúng tỉ lệ mà cổng thực sự đọc được biển.
    """
    items: List[Dict[str, object]] = list(rows)
    total = len(items)
    if total == 0:
        return {
            "total": 0,
            "recognized": 0,
            "recognition_rate": 0.0,
            "exact_match_strict": 0.0,
            "exact_match_relaxed": 0.0,
            "mean_cer": 0.0,
            "median_cer": 0.0,
            "mean_confidence": 0.0,
            "errors": 0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
        }

    recognized = [r for r in items if r.get("predicted")]
    errors = [r for r in items if r.get("error")]
    cers = [float(r["cer"]) for r in items]
    confidences = [
        float(r["confidence"]) for r in items if r.get("confidence") is not None
    ]
    latencies = [
        float(r["process_time"]) for r in items if r.get("process_time") is not None
    ]

    return {
        "total": total,
        "recognized": len(recognized),
        "recognition_rate": len(recognized) / total,
        "exact_match_strict": sum(1 for r in items if r["exact_strict"]) / total,
        "exact_match_relaxed": sum(1 for r in items if r["exact_relaxed"]) / total,
        "mean_cer": sum(cers) / total,
        "median_cer": percentile(cers, 0.5),
        "mean_confidence": (sum(confidences) / len(confidences)) if confidences else 0.0,
        "errors": len(errors),
        "latency_p50": percentile(latencies, 0.5),
        "latency_p95": percentile(latencies, 0.95),
    }


def group_by_tag(rows: Iterable[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """Bảng số tách theo `tags` (night · rain · blur · two_line · angled ...).

    Số tổng che mất chỗ hỏng: 85% trung bình có thể là 95% ban ngày và 40% ban
    đêm. Chỉ bảng tách theo điều kiện mới chỉ ra nên đi sửa cái gì.
    """
    buckets: Dict[str, List[Dict[str, object]]] = {}
    for row in rows:
        for tag in row.get("tags") or []:
            buckets.setdefault(str(tag), []).append(row)
    return {tag: aggregate(items) for tag, items in sorted(buckets.items())}
