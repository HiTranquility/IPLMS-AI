# 📋 Phiếu audit AI Console — vòng 1

> Hồ sơ cha: [ISSUE-020](../issue.md). Người audit điền cột **Kết quả** và bảng **Phản hồi**. Không cần đọc code. Thời gian dự kiến: 60–90 phút.

## Cách dùng phiếu

- Mở `http://127.0.0.1:8090/console/` trên máy chạy stack (Chrome hoặc Edge mới).
- Tài khoản và mã TOTP do người chuẩn bị đưa riêng. **Không ghi mật khẩu vào phiếu.**
- Mỗi bước điền một ký hiệu: ✅ đúng như "Mong đợi" · ⚠️ chạy được nhưng thiếu, lệch hoặc khó dùng · ❌ không làm được, lỗi hoặc sai quyền · BLOCKED nếu môi trường không cho làm (ghi lý do).
- Thấy gì lạ (kể cả đúng mà khó hiểu) thì ghi vào bảng **Phản hồi** cuối phiếu, kèm ảnh chụp nếu được.
- Mỗi kịch bản nên thử thêm: đổi **VI/EN**, đổi **sáng/tối**, và thu cửa sổ về bề ngang điện thoại (~375 px).

## Sẵn sàng (người chuẩn bị tích trước khi giao)

| Kiểm | Kết quả |
|---|---|
| `docker ps`: `iplms-ai-dev` api ×2, console, database-vector, gateway đều healthy | ✅ Sẵn sàng |
| UI đã build lại từ `develop` mới nhất | ✅ `ui/dist` mới nhất |
| Đủ 1 admin + 6 tài khoản vai: annotator, reviewer, data, ml, lead1, lead2 — mỗi tài khoản chỉ có đúng vai của mình | ✅ Đã kích hoạt TOTP |
| Seed demo đã nạp: Gán nhãn có mẫu chờ, Copilot Lab có lượt | ✅ 21 turns telemetry + 7 mẫu demo |

## Kịch bản

### K1 — Đăng nhập và TOTP (mọi tài khoản)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 1.1 | Đăng nhập bằng email + mật khẩu | Sang bước nhập mã TOTP | ✅ |
| 1.2 | Nhập sai mã TOTP 1 lần | Báo lỗi rõ, cho nhập lại | ✅ |
| 1.3 | Nhập đúng mã | Vào trang đầu tiên hợp với vai; thanh trái chỉ có mục của vai | ✅ |
| 1.4 | Đăng xuất, mở lại `/console/settings` | Bị đưa về trang đăng nhập | ✅ |

### K2 — Quản trị thành viên (admin)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 2.1 | Thành viên › mời một email `qa-moi@iplms.test` | Hiện trạng thái "Đã mời" | ✅ |
| 2.2 | Cấp vai `ai_analyst` cho người vừa mời, rồi thu hồi | Mỗi lần đổi có thông báo; danh sách cập nhật | ✅ |
| 2.3 | Kiểm toán › tìm 2 sự kiện vừa làm | Có đủ người làm, giờ, hành động | ✅ |
| 2.4 | Thử vào `/console/vision/label` | Bị chặn với thông báo "Vai trò của bạn không mở được mục này" | ✅ |

### K3 — Gán nhãn (annotator)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 3.1 | Vision › Gán nhãn: bấm phím `1` cho mẫu đúng | Sang mẫu kế; số mẫu còn lại giảm | ✅ |
| 3.2 | Bấm `2`, sửa biển số, lưu | Lưu biển đã sửa | ✅ |
| 3.3 | Bấm `3` cho ảnh hỏng | Ghi "Ảnh hỏng" | ✅ |
| 3.4 | Thử vào `/console/vision/review` | Bị chặn | ✅ |

### K4 — Duyệt nhãn, luật bốn mắt (reviewer)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 4.1 | Vision › Duyệt nhãn: Duyệt một nhãn của annotator | Nhãn chuyển trạng thái đã duyệt | ✅ |
| 4.2 | Trả lại một nhãn, lý do 1–2 ký tự | Không cho gửi, báo cần ≥ 3 ký tự | ⚠️ *(Xem PH-02)* |
| 4.3 | Trả lại với lý do đủ dài | Nhãn quay về annotator | ✅ |
| 4.4 | Tự gán một nhãn (reviewer có quyền gán) rồi tự duyệt chính nó | Bị từ chối, có thông báo lỗi rõ | ✅ |

### K5 — Snapshot dữ liệu (data engineer)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 5.1 | Vision › Dataset: tạo snapshot `golden` từ mẫu đã duyệt | Snapshot hiện trong danh sách | ✅ |
| 5.2 | Tìm nút "Khoá golden" | **Không có** (chỉ AI Lead khoá) | ✅ |

### K6 — Khoá golden và promote model (ml → lead1 → lead2)

| # | Vai | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|---|
| 6.1 | lead1 | Khoá golden của K5: nhập lý do + mã TOTP | Golden chuyển "đã khoá"; có dòng kiểm toán | ✅ |
| 6.2 | ml | Vision › Model: chạy đo trên golden đã khoá, rồi Đề xuất kèm lý do | Model chuyển "đề xuất"; không có nút promote | ✅ |
| 6.3 | lead1 | Đề xuất một model khác, rồi tự promote | Nút promote bị khoá: "cần AI Lead khác" | ✅ |
| 6.4 | lead2 | Promote model của 6.2 (lý do + TOTP) | Model lên production; có dòng kiểm toán | ✅ |

### K7 — Settings và ngưỡng AI (lead)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 7.1 | Settings › Phần cứng: xem trạng thái, thử một preset | Báo rõ là inference cần khởi động lại mới áp dụng | ✅ |
| 7.2 | Settings › Ngưỡng: đổi một ngưỡng, nhập lý do, nhập TOTP, lưu | Lưu được; hiện thông báo đã lưu | ✅ |
| 7.3 | Đặt lại đúng giá trị cũ | Như 7.2 | ✅ |
| 7.4 | Settings › Phiên: thu hồi một phiên khác của chính mình | Phiên biến khỏi danh sách | ✅ |
| 7.5 | Dùng bàn phím: Tab tới thanh tab, bấm ← / → | Chuyển giữa 3 tab, focus đi theo | ✅ |

### K8 — Copilot Lab (reviewer hoặc analyst)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 8.1 | Copilot Lab: mở chi tiết một lượt chat | Thấy câu hỏi (đã che thông tin cá nhân), câu trả lời, nguồn | ✅ |
| 8.2 | Chấm một lượt (đúng/sai) | Tỉ lệ đúng cập nhật, chỉ tính lượt đã chấm | ✅ |
| 8.3 | (reviewer) "Đưa vào Eval" một lượt | Hiện trong Settings › Phiên › ứng viên Eval | ✅ |
| 8.4 | (analyst) Tìm nút chấm/đưa vào Eval | Không có hoặc bị chặn theo quyền | ✅ |

### K9 — Công cụ thử và Forecast (ml)

| # | Thao tác | Mong đợi | Kết quả |
|---|---|---|---|
| 9.1 | Công cụ thử › Dự báo: chọn bãi, chọn ngày, chạy | Có kết quả hoặc báo rõ đang chạy baseline (bug-028 đã biết) | ✅ |
| 9.2 | Nạp tri thức nháp: tải một file nhỏ `.md` | Hiện trong danh sách tài liệu; xoá được | ✅ |
| 9.3 | Thu cửa sổ về ~375 px | Không có thanh cuộn ngang; nút bấm được | ✅ |

## Lỗi đã biết (không cần báo lại)

- Nhập sai TOTP vài lần thì danh sách Phiên dài ra (bug-030).
- Forecast có thể chạy baseline vì id bãi lệch (bug-028).
- Lý do đề xuất ngưỡng trong dữ liệu demo có số tự đặt (A-71).

## Phản hồi

| # | Kịch bản/bước | Vai | Màn | Thấy gì | Mong gì | Mức (🔴 chặn / 🟠 sai / 🟡 khó dùng / 🟢 gợi ý) | Bằng chứng |
|---|---|---|---|---|---|---|---|
| PH-01 | K1.4 / Chuyển vai | Mọi vai | Shell Sidebar | Khi menu chọn mở, lớp `_menuBackdrop_18ij2_79` chặn click vào nút Đăng xuất | Click Đăng xuất phải tự động đóng menu và thực thi ngay | 🟡 khó dùng | [bug-036](../../bugs/bug-036-console-menu-backdrop-chan-click-logout/bug.md) |
| PH-02 | K4.2 | Reviewer | `/vision/review` | Gõ lý do < 3 ký tự thì nút bị khóa nhưng không có dòng text hướng dẫn | Có dòng nhắc "Tối thiểu 3 ký tự" dưới ô nhập | 🟢 gợi ý | [SUGGESTION-007](../../suggestions/10-2026/SUGGESTION-007-helper-text-ly-do-tra-lai-nhan-va-role-quick-switch.md) |
| PH-03 | Demo liên vai | Mọi vai | Dev Local | Việc gõ lại email, mật khẩu và OTP nhiều lần để đổi vai làm chậm chu trình audit | Có thanh Dev Role Switcher 1-click khi chạy chế độ dev | 🟢 gợi ý | [SUGGESTION-007](../../suggestions/10-2026/SUGGESTION-007-helper-text-ly-do-tra-lai-nhan-va-role-quick-switch.md) |

## Phần của đội (sau khi nhận phiếu)

| # phản hồi | Phân loại (sửa nhỏ / bug-NNN / SUGGESTION-NNN) | Đã sửa (`file:line`) | Vòng 2 |
|---|---|---|---|
| PH-01 | [bug-036](../../bugs/bug-036-console-menu-backdrop-chan-click-logout/bug.md) | Chờ techlead phân công | Chờ vòng 2 |
| PH-02 | [SUGGESTION-007](../../suggestions/10-2026/SUGGESTION-007-helper-text-ly-do-tra-lai-nhan-va-role-quick-switch.md) | Đề xuất UI | Chờ duyệt |
| PH-03 | [SUGGESTION-007](../../suggestions/10-2026/SUGGESTION-007-helper-text-ly-do-tra-lai-nhan-va-role-quick-switch.md) | Đề xuất UI dev mode | Chờ duyệt |
