# `model/artifacts/` — chỉ dành cho bootstrap

- `bootstrap/`: weight nhỏ cần để clone repo rồi chạy được service; hiện chỉ có detector ANPR kế thừa.
- Candidate/accepted model có version nằm trong object storage private, không commit vào Git.
- Runtime tải model qua signed URL, kiểm SHA-256 rồi cache tại `var/model-cache/<model>/<version>/`.

Không ghi đè một tên `best.pt` cho các lần train mới. Mỗi bản phát hành phải có version, checksum, manifest dataset và metrics đi kèm trong model catalog.
