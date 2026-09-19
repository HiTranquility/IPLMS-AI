"""Bộ test của AI service.

Dùng `unittest` của thư viện chuẩn, CỐ Ý không thêm dependency: bộ test phải
chạy được ngay trên máy chỉ mới `pip install -r requirements.txt`. Có pytest thì
`pytest ai/tests` vẫn chạy được y nguyên vì pytest hiểu test kiểu unittest.

Chạy:  cd ai && python -m unittest discover -s tests -t .
"""
