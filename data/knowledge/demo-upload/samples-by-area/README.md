# Bộ dữ liệu mẫu Biểu phí & Quy chế đa định dạng theo từng Bãi đỗ xe (RAG Copilot & Tariff)

Thư mục này chứa **150 file mẫu trên 6 định dạng** (`.md`, `.txt`, `.docx`, `.pdf`, `.csv`, `.json`) cho 25 bãi đỗ xe tiêu biểu nhất hệ thống (cùng toàn bộ 503 bãi đỗ xe đã được nạp & xuất bản `PUBLISHED` trực tiếp vào `pgvector`).

| STT | Tên bãi đỗ xe | Mã bãi (UUID) | Giá chuẩn/giờ | Cao điểm sáng | Cao điểm tối | Qua đêm | Thư mục 6 định dạng |
|---|---|---|---|---|---|---|---|
| 1 | **Bãi xe Sân bay Tân Sơn Nhất** | `a749772f-62db-42f5-a993-2c40f317714f` | 20.000đ | 23.000đ | 25.000đ | 70.000đ | `./bai-xe-tan-son-nhat/` (6 files) |
| 2 | **Bãi xe Landmark 81** | `efb73d46-8eb2-4358-b38a-a8704fdefbd5` | 25.000đ | 29.000đ | 31.000đ | 90.000đ | `./bai-xe-landmark-81/` (6 files) |
| 3 | **Bãi xe Aeon Mall Tân Phú Celadon** | `3c2abaee-18c9-4033-b3f8-90a514c7ec7f` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-aeon-tan-phu/` (6 files) |
| 4 | **Bãi xe Vincom Center Đồng Khởi** | `b24dde69-3b92-4e32-99c5-86d65b269b71` | 25.000đ | 29.000đ | 31.000đ | 90.000đ | `./bai-xe-vincom-dong-khoi/` (6 files) |
| 5 | **Bãi xe Bitexco Financial Tower** | `6dc07208-e051-4750-8e02-e5004e06c123` | 30.000đ | 34.000đ | 38.000đ | 105.000đ | `./bai-xe-bitexco-tower/` (6 files) |
| 6 | **Bãi xe Aeon Mall Bình Tân** | `3d985024-e6f9-400e-acc6-0a6fca91d331` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-aeon-binh-tan/` (6 files) |
| 7 | **Bãi xe Khách sạn & Hội nghị Nguyễn Tri Phương (Q5-213)** | `df1e5ff4-f1d3-4086-94b9-23d3f46ba8d8` | 25.000đ | 29.000đ | 31.000đ | 90.000đ | `./bai-xe-q5-nguyen-tri-phuong-213/` (6 files) |
| 8 | **Bãi xe Công cộng Phan Đăng Lưu (BT-076)** | `16c93376-862e-4abd-b2ce-3ffde430af48` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-bt-phan-dang-luu-76/` (6 files) |
| 9 | **Bãi xe Tổ hợp Căn hộ & Thương mại Ung Văn Khiêm (BT-426)** | `eb24ff14-777c-40be-9227-fb80bc6b0f37` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-bt-ung-van-khiem-426/` (6 files) |
| 10 | **Bãi xe Trung tâm Thể thao & Giải trí Đỗ Xuân Hợp (TĐ-289)** | `189a8402-75fe-403e-a761-9cbf6298684a` | 30.000đ | 34.000đ | 38.000đ | 105.000đ | `./bai-xe-td-do-xuan-hop-289/` (6 files) |
| 11 | **Bãi xe Tòa nhà Văn phòng Võ Văn Tần (Q3-152)** | `78fdae3d-fa63-49e1-88e7-2c2774504cf4` | 20.000đ | 23.000đ | 25.000đ | 70.000đ | `./bai-xe-q3-vo-van-tan-152/` (6 files) |
| 12 | **Bãi xe Khách sạn & Hội nghị Tô Hiến Thành (Q10-365)** | `b3ce1a3f-9e15-4114-bd3c-e867cf2f8d11` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-q10-to-hien-thanh-365/` (6 files) |
| 13 | **Bãi xe Công cộng Âu Cơ (TB-228)** | `14ca4ca8-09bd-4334-b1ee-f84fca5dc8a8` | 25.000đ | 29.000đ | 31.000đ | 90.000đ | `./bai-xe-tb-au-co-228/` (6 files) |
| 14 | **Bãi xe Bệnh viện Đa khoa Hàm Nghi (Q1-091)** | `7636abd4-7d67-4568-afce-d4cc6b3a3b5a` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-q1-ham-nghi-91/` (6 files) |
| 15 | **Bãi xe Trung tâm Thể thao & Giải trí Hàm Nghi (Q1-441)** | `efd024a2-cb56-4e95-b351-039b3f0f2700` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-q1-ham-nghi-441/` (6 files) |
| 16 | **Bãi xe Tòa nhà Văn phòng Huỳnh Tấn Phát (Q7-304)** | `56330c31-f895-4912-bf94-847f3f7e64b6` | 30.000đ | 34.000đ | 38.000đ | 105.000đ | `./bai-xe-q7-huynh-tan-phat-304/` (6 files) |
| 17 | **Bãi xe TTTM & Mua sắm Phan Đăng Lưu (PN-167)** | `c8f31d55-9a5c-45c3-9ecb-96b1168a5038` | 20.000đ | 23.000đ | 25.000đ | 70.000đ | `./bai-xe-pn-phan-dang-luu-167/` (6 files) |
| 18 | **Bãi xe Chung cư Cao cấp Phạm Văn Chiêu (GV-030)** | `bc7180a1-0569-4153-83b2-941a53eba22b` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-gv-pham-van-chieu-30/` (6 files) |
| 19 | **Bãi xe Công cộng Phạm Văn Chiêu (GV-380)** | `bf9ac86a-c775-42f5-a4f3-bd3f30f4af97` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-gv-pham-van-chieu-380/` (6 files) |
| 20 | **Bãi xe Bệnh viện Đa khoa Trần Phú (Q5-243)** | `26be7495-5890-4066-9f9c-437b02c12875` | 25.000đ | 29.000đ | 31.000đ | 90.000đ | `./bai-xe-q5-tran-phu-243/` (6 files) |
| 21 | **Bãi xe Tòa nhà Văn phòng Điện Biên Phủ (BT-456)** | `9d90d659-b73c-4719-97f4-6724589b2bf2` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-bt-dien-bien-phu-456/` (6 files) |
| 22 | **Bãi xe Tổ hợp Căn hộ & Thương mại Ung Văn Khiêm (BT-106)** | `0f2ad9d0-894e-411b-938e-1dcb93cda246` | 15.000đ | 17.000đ | 19.000đ | 50.000đ | `./bai-xe-bt-ung-van-khiem-106/` (6 files) |
| 23 | **Bãi xe TTTM & Mua sắm Đỗ Xuân Hợp (TĐ-319)** | `b5ebd5b3-c19a-4374-bb98-663f7150e818` | 30.000đ | 34.000đ | 38.000đ | 105.000đ | `./bai-xe-td-do-xuan-hop-319/` (6 files) |
| 24 | **Bãi xe Chung cư Cao cấp Trương Định (Q3-182)** | `4799659c-2981-4e6d-811e-70eb89419572` | 20.000đ | 23.000đ | 25.000đ | 70.000đ | `./bai-xe-q3-truong-dinh-182/` (6 files) |
| 25 | **Bãi xe Saigon Centre & Takashimaya** | `968b6832-1dff-4b25-8004-13699240c8d8` | 25.000đ | 29.000đ | 31.000đ | 90.000đ | `./bai-xe-saigon-centre/` (6 files) |
