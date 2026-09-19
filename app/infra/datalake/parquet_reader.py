"""Đọc dữ liệu lịch sử các lượt gửi xe (parking sessions) từ Data Lake dạng Apache Parquet."""
from typing import List, Dict, Any
from app.config import get_config
from app.utils.logger import logger

class ParquetReader:
    """Reader đọc logs lịch sử phục vụ việc huấn luyện và dự báo Occupancy."""

    def __init__(self, base_path: str | None = None):
        self.base_path = base_path or get_config().datalake.local_path

    def load_historical_occupancy(self, parking_lot_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Đọc và aggregate dữ liệu chuỗi thời gian (time-series) theo từng mốc 30 phút."""
        logger.info(f"Loading historical parquet logs for lot={parking_lot_id}, last {days} days...")
        
        # Mẫu dữ liệu mô phỏng
        return [
            {"hour": 8, "day_of_week": 1, "avg_occupancy": 0.45},
            {"hour": 12, "day_of_week": 1, "avg_occupancy": 0.85},
            {"hour": 18, "day_of_week": 1, "avg_occupancy": 0.92},
            {"hour": 22, "day_of_week": 1, "avg_occupancy": 0.30},
        ]

parquet_reader = ParquetReader()
