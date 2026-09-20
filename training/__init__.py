"""Script train/eval cho các model của `ai/`.

Là package CHỈ để `test/` import được phần logic thuần (`plate_metrics`) mà
không phải nạp model. Các script còn lại vẫn chạy kiểu `python training/<x>.py`
và tự thêm `ai/` vào `sys.path` như trước — không đổi cách chạy nào.
"""
