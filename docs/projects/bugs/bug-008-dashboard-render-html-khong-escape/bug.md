# 🐛 bug-008: Dashboard mới render câu hỏi và câu trả lời bằng innerHTML

> **Đích:** `docs/projects/bugs/bug-008-dashboard-render-html-khong-escape/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

## 📌 Meta

| | |
|---|---|
| **Trạng thái / Mức độ** | 🆕 New — phát hiện trên nhánh chưa merge / P1 |
| **Người báo / Ngày** | Codex root + review agents / 2026-10-15 |
| **Revision** | `origin/khoa-develop` tại `9a1aafd`; so base `6dd8547`, đối chiếu develop `c80037d` |
| **Nguồn** | IPLMS AUDIT-008; nhánh này chưa được nhận vào develop |

## Hành vi thực tế

Câu hỏi ${text}, answer ${ans.answer} và sources được nội suy trực tiếp vào chuỗi HTML rồi gán innerHTML. Payload chứa thẻ HTML có thể tạo node/handler hoặc request tài nguyên ngoài khi hiển thị. Đây là sink mới ở dashboard được app/main.py phục vụ, không phải lỗi của frontend hiện hành.

## Hành vi mong đợi

Hiển thị dữ liệu người dùng/LLM bằng textContent; không tự render HTML/link/ảnh theo ADR-0029 luật3.

## Tái hiện / bằng chứng

Vị trí **thuộc snapshot9a1aafd**, không phải file develop hiện tại: `static/index.html:1079–1091,1108–1122`. Đọc bằng `git show 9a1aafd:<đường-dẫn>` trong repo AI.

Đối chiếu source9a1aafd static/index.html và app/main.py. Chưa mở dashboard remote, chưa thực thi payload/browser và không gọi CDN/LLM. Xác nhận thiếu escape ở sink; phạm vi khai thác thực tế cần kiểm browser local có cô lập network.

## Sửa / kiểm chứng

Dùng DOMtext an toàn cho query/answer/sources; test payloadHTML bằng fixture local không truy cập mạng. Không thêm sanitizer chỉ để giữ tính năng render HTML không cần thiết. Chưa sửa.

- [ ] Đã sửa và chạy kiểm tập trung tương ứng.
- [ ] Đã kiểm tích hợp tại revision nhận vào develop; không lấy source review thay cho runtime.
