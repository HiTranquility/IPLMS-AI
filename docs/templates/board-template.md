# 📋 BOARD — <tên repo>: việc chưa làm, ai nhận, tới đâu

> **Đích:** `docs/projects/BOARD.md` — *một file của repo này, không theo tháng, không có mã* · **Luật chung:** [templates/README](README.md)
> **Không viết tay.** Từ IPLMS ADR-0060, `BOARD.md` sinh từ Meta hồ sơ bằng `python -X utf8 script/board_gen.py`; CI (`.github/workflows/generated-docs.yml`) sinh lại sau mỗi lần merge vào `develop`, PR sửa `BOARD.md` bị `script/check_generated.py` chặn. Repo mới: chép hai script + workflow từ gốc IPLMS, tạo file này chỉ với dòng tiêu đề `#` ở trên (bộ sinh giữ dòng đó), để CI sinh phần còn lại.

## Bảng lấy dữ liệu từ đâu

| Cột BOARD | Lấy từ hồ sơ (bug, ISSUE, CHORE, SUGGESTION; PROB/IDEA/AUDIT/REQ khi có Người nhận hoặc bảng việc) |
|---|---|
| Mục 🙋 / 🗓️ / 🚧 / ⏳ / ⛔ / ✅ | **Trạng thái** (đầu dòng 🚧/🛠️ → 🚧, 👀/🔄 → ⏳, "Bị chặn" → ⛔, ✅ → ✅); chưa bắt đầu mà có Người nhận → 🗓️, không có → 🙋 |
| Người nhận · Hạn · Ưu tiên | Meta **Người nhận**, **Hạn** (`YYYY-MM-DD`), **Ưu tiên** (🔴/🟠/🟡/🟢) |
| ✅ Xong gần đây | Meta **Ngày đóng**; 20 hồ sơ mới nhất |
| Nhiều dòng cho một hồ sơ | Mục `## 📋 Việc trên BOARD` trong hồ sơ: `\| Việc \| Người nhận \| Hạn \| Ưu tiên \| Trạng thái \|` |

## Luật

1. **Mọi dòng có hồ sơ trong chính repo này.** Việc bắt nguồn từ repo gốc → mở ISSUE ở repo này ghi `Bắt nguồn từ: IPLMS …`, mô tả đủ để làm mà không cần đọc gốc; nhiều việc con của cùng một hồ sơ gốc gom vào bảng `📋 Việc trên BOARD` của ISSUE đó.
2. **Nhận việc** = điền **Người nhận** + **Hạn**, đổi Trạng thái sang 🚧. **Xong** = Trạng thái ✅ + **Ngày đóng**.
3. Ưu tiên: 🔴 hỏng luồng chính / bảo mật / mất dữ liệu · 🟠 sai nhưng có đường vòng, hoặc kiểm thử còn treo · 🟡 nên làm · 🟢 dọn dẹp, vận hành nhỏ.
