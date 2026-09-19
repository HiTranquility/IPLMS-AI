# `data/golden/plates/` — Bộ vàng đo độ chính xác đọc biển số

> Quyết định chi phối: [SUGGESTION-007 §B1](../../../../docs/suggestions/09-2026/SUGGESTION-007-vision-deep-dive-roadmap.md) · [ADR-0003 §4](../../../../docs/projects/adrs/0003-duong-du-lieu-vision-tu-phien-do-toi-checkpoint.md)

Đây là **thước đo** của pipeline ANPR. Không có nó thì mọi thay đổi model, mọi
lần tinh chỉnh tham số, mọi đề xuất "đổi sang PaddleOCR" đều là cảm tính —
SUGGESTION-007 vì vậy đặt B1 **chặn** toàn bộ B2–B5 và C4.

## Cái gì vào git, cái gì không

| Vào git | Không vào git |
|---|---|
| `manifest.json` — nhãn do người gán, **mất là không dựng lại được** | `images/` — ảnh biển số là **PII** và nặng |
| `README.md` (file này) | |
| `reports/*.json` — số đo từng lần chạy, nhẹ, là bằng chứng "trước/sau" | |

**[NEVER] commit ảnh.** Luật ở ADR-0003 §4.

## Dựng bộ vàng

### 1. Nạp ảnh + nhãn

Dataset công khai mỗi bộ gói nhãn một kiểu; script quy cả ba kiểu hay gặp về
cùng một `manifest.json`:

```bash
cd ai

# Biển số nằm trong tên file:  51F17812.jpg
python training/import_plate_dataset.py --from filename --src ~/Downloads/vn-plates

# Mỗi ảnh kèm một .txt cùng tên chứa biển số
python training/import_plate_dataset.py --from sidecar --src ~/Downloads/ds

# Một file CSV có cột ảnh + cột biển số
python training/import_plate_dataset.py --from csv --src ~/Downloads/ds \
    --csv labels.csv --image-column image --plate-column plate
```

Thêm `--dry-run` để xem trước khi ghi. Ảnh được **copy** vào `images/` và đặt
tên theo hash, nên nạp trùng hai lần vẫn chỉ vào bộ vàng một lần.

### 2. Gắn tag theo điều kiện ảnh

`eval_plates.py` in bảng số **tách theo tag**. Số tổng che mất chỗ hỏng: 85%
trung bình có thể là 95% ban ngày và 40% ban đêm — chỉ bảng tách mới chỉ ra nên
đi sửa cái gì.

Tag nên dùng: `night` · `rain` · `blur` · `angled` · `two_line` (biển vuông 2
dòng của xe máy) · `dirty` · `motorbike` · `car`.

```bash
python training/import_plate_dataset.py --from filename --src ~/Downloads/night-set --tags night,blur
```

Nạp xong sửa tay `manifest.json` cũng được — nó là file người đọc được.

### 3. Đo

```bash
python training/eval_plates.py                 # cả bộ
python training/eval_plates.py --tag night     # chỉ ảnh ban đêm
python training/eval_plates.py --label before-B2
```

## Đọc con số ra sao

| Chỉ số | Nghĩa |
|---|---|
| `recognition_rate` | Tỉ lệ lượt đọc **ra được** một chuỗi (không `UNKNOWN`, không lỗi) |
| `exact_match_strict` | Khớp **nguyên văn** cả gạch ngang và dấu chấm: `51F-178.12` |
| `exact_match_relaxed` | Khớp sau khi bỏ dấu phân cách: `51F17812` cũng tính đúng |
| `mean_cer` | Sai bao nhiêu **ký tự** trên mỗi ký tự nhãn (0 = hoàn hảo) |
| `latency_p95` | 5% lượt chậm nhất chậm tới đâu |

**[GOTCHA] Khoảng cách `strict` ↔ `relaxed` chính là việc B2.** OCR hiện đọc
`86A094.70` trong khi biển thật là `86A-094.70`. Backend tra xe bằng so khớp
**chuỗi chính xác** (`vehicle.licensePlate = :trimmedPlate`), nên thiếu gạch =
không khớp được xe của thành viên và người đó bị tính như khách vãng lai. Hậu xử
lý định dạng biển VN lấy về đúng khoảng cách đó mà **không cần đổi model**.

## Kỷ luật

- **[MUST]** Mọi PR đụng model hoặc pipeline nhận diện phải kèm số **trước và
  sau** trên cùng bộ vàng này. Không có số ⇒ không merge.
- **[NEVER]** Sửa nhãn trong `manifest.json` để con số đẹp lên. Nhãn sai thì sửa
  và **nói rõ đã sửa gì**; nhãn đúng mà model đọc sai là kết quả cần giữ nguyên.
- **[NEVER]** Dùng ảnh của bộ vàng để train hay tinh chỉnh bất cứ thứ gì. Ảnh đã
  thấy lúc train thì điểm đo trên nó là điểm giả (ADR-0003 §3).

## ⚠️ Dataset công khai không thay được ảnh cổng thật

ADR-0003 §1 đã chốt: ảnh web khác hoàn toàn ảnh camera cổng về góc máy, ánh sáng
và độ nhoè. Số đo trên dataset công khai là **mốc để so tương đối giữa các lần
sửa**, không phải con số sẽ thấy ở cổng thật.

Ảnh thật đến từ `parking_session.check_in_image_url` / `check_out_image_url`
(phần thu thập đã dựng trong ISSUE-003). Có ảnh thật thì nạp vào và đo lại — và
ghi rõ trong `reports/` là số nào đo trên tập nào.
