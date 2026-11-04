# 🐛 bug-056: ISSUE-007 và ISSUE-020 mỗi mã có hai hồ sơ trên `develop`

> **Đích:** `docs/projects/bugs/bug-056-trung-ma-issue-007-va-issue-020/bug.md` · **Luật chung:** [templates/README](../../../templates/README.md)

| | |
|---|---|
| **Trạng thái** | 🆕 New — hướng sửa soạn sẵn ở [IPLMS ISSUE-139 phase-1](../../../../../docs/projects/issues/11-2026/ISSUE-139-ma-ho-so-khong-trung/phase/phase-1.md) task 1.6 |
| **Người nhận** | @HiTranquility |
| **Hạn** | |
| **Ưu tiên** | 🟠 |
| **Ngày đóng** | |
| **Người báo** | Claude Code, khi rà mã trùng cho IPLMS [REQ-029](../../../../../docs/requirements/11-2026/REQ-029-ma-ho-so-khong-trung-khi-ho-so-tang.md) |
| **Ngày** | 2026-11-03 |
| **Môi trường** | `origin/develop` và `origin/main` (fetch 2026-11-03) |
| **Nhánh** | `chore/ISSUE-139-2026-11-record-id-merge-gate` |

## Hành vi thực tế

Trên cả `origin/develop` lẫn `origin/main`, trong `docs/projects/issues/10-2026/`:

| Mã | Hồ sơ | Thêm lúc |
|---|---|---|
| ISSUE-007 | `ISSUE-007-copilot-rag-heldout-dataset` | 2026-10-24 `d66b3a5` |
| ISSUE-007 | `ISSUE-007-console-tools-and-knowledge-management` | 2026-10-25 `2c15323` |
| ISSUE-020 | `ISSUE-020-vision-anpr-pipeline-and-vision-lab-upgrade` | 2026-10-26 `fd82398` |
| ISSUE-020 | `ISSUE-020-ke-hoach-demo-audit-ai-console` | 2026-10-26 `b5ff366` |

Link "ai ISSUE-007" / "ai ISSUE-020" từ gốc IPLMS hoặc từ hồ sơ khác vì vậy không biết đang trỏ hồ sơ nào. BOARD sinh ra hai dòng cùng mã.

## Hành vi mong đợi

Mỗi mã một hồ sơ. Bản thêm trước giữ số, bản sau đổi sang mã kế tiếp (IPLMS ADR-0068 D4, tiền lệ IPLMS bug-054).

## Tái hiện

Ở gốc IPLMS:
```bash
python -X utf8 script/next_record_id.py
```
Mục "Mã trùng" có `ai ISSUE-007` và `ai ISSUE-020`, mỗi mã hai slug, cả hai nằm trên `develop`.

## Nguyên nhân gốc

Hai phiên lấy cùng số kế tiếp trước khi phiên kia push. `next_record_id.py` chỉ gợi ý (luôn exit 0), không có gì kiểm lúc push hay merge.

## Hướng sửa (soạn sẵn)

1. ISSUE-007: giữ `copilot-rag-heldout-dataset`; `console-tools-and-knowledge-management` đổi sang mã kế tiếp lúc làm (lúc viết: ISSUE-030).
2. ISSUE-020: cùng ngày nên so giờ bằng `git log --diff-filter=A --format='%h %aI' origin/develop -- <thư mục>`; bản sau đổi số (lúc viết: ISSUE-031).
3. Mỗi hồ sơ đổi số: `git mv`, sửa tiêu đề, thêm dòng "**Đổi số …** (IPLMS ISSUE-139)" ở đầu; sửa link ở ai (`grep -rn "ISSUE-007-console\|ISSUE-020-<slug-bị-đổi>" docs`) và ở gốc IPLMS.
4. Chặn tái diễn: IPLMS ISSUE-139 phase-2/3 (pre-push + CI).

## Sửa / kiểm chứng

*(Điền khi sửa.)*
- [ ] `next_record_id.py` ở gốc không còn `ai ISSUE-007` / `ai ISSUE-020`.
- [ ] Không còn link tới slug cũ (`grep` ở ai và gốc).
