# 🐛 bug-036: Menu Backdrop Chặn Click Nút Đăng Xuất Khi Đổi Vai Trò Trên AI Console

> **Đích:** `docs/projects/bugs/bug-036-console-menu-backdrop-chan-click-logout/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | ✅ Fixed |
| **Người nhận** | @HiTranquility |
| **Hạn** | 2026-10-31 |
| **Ưu tiên** | 🟡 |
| **Ngày đóng** | 2026-10-26 |
| **Người báo** | Antigravity Pair Programming (Phát hiện qua Browser Control) |
| **Ngày báo** | 2026-10-26 |
| **Môi trường** | local / develop (`http://localhost:8090/`) |

---

## Hành vi thực tế

Khi người dùng mở một menu thả xuống (dropdown) hoặc menu góc dưới của console (như chọn theme, danh sách vai trò hoặc menu điều hướng), một lớp phủ vô hình `_menuBackdrop_18ij2_79` xuất hiện trên toàn bộ màn hình để bắt sự kiện click ra ngoài nhằm đóng menu.

Tuy nhiên, lớp phủ này chặn toàn bộ sự kiện con trỏ chuột (`pointer-events`), khiến các thao tác click trực tiếp vào nút **"Đăng xuất"** hoặc chuyển trang bị chặn lại (`intercepts pointer events`). Thư viện tự động hóa Playwright ghi nhận lỗi:
```text
playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("button:has-text('Đăng xuất')").first
  - done scrolling
  - <div aria-hidden="true" class="_menuBackdrop_18ij2_79"></div> intercepts pointer events
```

Về mặt trải nghiệm người dùng thực tế (UX "sạn"):
Người dùng bấm vào nút Đăng xuất thì không có phản hồi gì ở lần bấm đầu tiên; họ buộc phải bấm ra một vùng trống bất kỳ để tắt menu đang mở rồi mới bấm lại nút Đăng xuất lần thứ hai.

---

## Hành vi mong đợi

1. Khi người dùng click vào bất kỳ nút bấm hoặc liên kết điều hướng nào (kể cả nút Đăng xuất) khi menu đang mở:
   - Menu đang mở phải lập tức đóng lại.
   - Thao tác click vào nút mục tiêu phải được tiếp nhận và thực thi ngay lập tức mà không bị lớp backdrop chặn (hoặc backdrop tự động tiêu biến ngay khi con trỏ chuột rời khỏi vùng menu).
2. Hoặc cấu hình CSS `pointer-events: none` cho backdrop đối với các phần tử điều hướng cấp cao.

---

## Tái hiện

1. Đăng nhập vào AI Console tại `http://localhost:8090/` với tài khoản bất kỳ.
2. Mở một menu lựa chọn (ví dụ: mở switcher chọn giao diện hoặc menu người dùng).
3. Không bấm ra ngoài để đóng menu, mà di chuột và click trực tiếp vào nút **Đăng xuất** ở góc dưới thanh điều hướng.
4. **Quan sát:** Nút Đăng xuất không nhận click ở lần đầu do lớp backdrop `_menuBackdrop_18ij2_79` che phủ.

---

## Bằng chứng

- File CSS liên quan: `ai/ui/src/components/layout/Shell/Shell.module.css` (hoặc module menu liên quan).
- Log trích xuất từ kịch bản chạy tự động Playwright `live_cross_role_visual_interactive.py`:
  ```text
  - <div aria-hidden="true" class="_menuBackdrop_18ij2_79"></div> from <div class="_wrap_18ij2_1 ">…</div> subtree intercepts pointer events
  ```

---

## Sửa / kiểm chứng

1. **Thay thế cơ chế backdrop overlay:**
   - Trong `ui/src/components/layout/PersonaSwitcher.tsx`, loại bỏ phần tử DOM full-screen `<div className={styles.menuBackdrop} ... />`.
   - Sử dụng `wrapRef = useRef<HTMLDivElement>(null)` kết hợp lắng nghe sự kiện `pointerdown` và `keydown (Escape)` trên `document`.
   - Khi người dùng click vào bất kỳ đâu ngoài dropdown (kể cả nút Đăng xuất), dropdown lập tức đóng lại đồng thời sự kiện click gốc vẫn truyền tới nút mục tiêu trong cùng 1 lần click.
2. **Dọn dẹp CSS:**
   - Xóa bỏ selector `.menuBackdrop` trong `ui/src/components/layout/PersonaSwitcher.module.css`.
3. **Kiểm chứng:**
   - `vitest run "PersonaSwitcher"`: 3/3 tests passed.
   - `tsc --noEmit && vite build`: biên dịch thành công 0 lỗi.
   - Trực tiếp click chuột vào các nút xung quanh khi Persona dropdown đang mở: sự kiện được tiếp nhận và phản hồi ngay lập tức.
