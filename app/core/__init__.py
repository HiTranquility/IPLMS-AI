"""Tầng chứa các Domain Nghiệp vụ AI (Vision, Copilot, Forecast, Knowledge).

Mỗi domain có đúng ba thư mục con `dtos/` `engines/` `services/` — xem
AI_CONVENTIONS §2. Hằng số / enum / exception dùng chung nhiều domain nằm ở gốc
tầng này (`constants.py` `enums.py` `exceptions.py`), **[NEVER]** khai bên trong
một domain rồi cho domain khác import sang.
"""
