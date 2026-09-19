"""Script seed dữ liệu lịch sử các lượt gửi xe (Data Lake Parquet / JSON logs).
Mô phỏng 30 ngày dữ liệu check-in/out tại các bãi xe phục vụ huấn luyện Time-Series Forecast Model.
"""
import os
import json
import random
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

PARKING_LOTS = [
    {"id": "lot_landmark_81", "name": "Bãi xe Landmark 81", "capacity": 500},
    {"id": "lot_vincom_center", "name": "Bãi xe Vincom Đồng Khởi", "capacity": 350},
    {"id": "lot_bitexco", "name": "Bãi xe Bitexco Financial Tower", "capacity": 200},
]

VEHICLE_TYPES = ["car_sedan", "car_suv", "motorbike", "truck"]

def generate_historical_logs(days: int = 30):
    ai_dir = Path(__file__).resolve().parent.parent.parent
    datalake_dir = ai_dir / "data" / "datalake" / "silver" / "parking_sessions"
    datalake_dir.mkdir(parents=True, exist_ok=True)

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    records = []
    current_time = start_time

    # Bước nhảy 30 phút
    while current_time < end_time:
        hour = current_time.hour
        weekday = current_time.weekday() # 0 = Thứ 2, 5 = Thứ 7, 6 = CN

        for lot in PARKING_LOTS:
            # Hệ số lưu lượng theo giờ cao điểm
            if 7 <= hour <= 9: # Cao điểm sáng
                base_occupancy = random.uniform(0.70, 0.92)
            elif 11 <= hour <= 13: # Giờ trưa ăn uống
                base_occupancy = random.uniform(0.65, 0.85)
            elif 17 <= hour <= 20: # Cao điểm tối
                base_occupancy = random.uniform(0.80, 0.98) if weekday >= 4 else random.uniform(0.75, 0.90)
            elif 22 <= hour or hour <= 5: # Ban đêm
                base_occupancy = random.uniform(0.10, 0.35)
            else:
                base_occupancy = random.uniform(0.40, 0.65)

            occupied_count = int(lot["capacity"] * base_occupancy)
            free_spots = lot["capacity"] - occupied_count

            records.append({
                "timestamp": int(current_time.timestamp()),
                "datetime_iso": current_time.isoformat(),
                "parking_lot_id": lot["id"],
                "parking_lot_name": lot["name"],
                "capacity": lot["capacity"],
                "occupied_spots": occupied_count,
                "free_spots": free_spots,
                "occupancy_percent": round(base_occupancy * 100, 2),
                "day_of_week": weekday,
                "hour_of_day": hour,
            })

        current_time += timedelta(minutes=30)

    # 1. Lưu ra file JSON mẫu
    json_path = datalake_dir / "historical_occupancy_30d.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"[OK] Created {len(records)} historical parking records to: {json_path}")

    # 2. Thử lưu dạng Apache Parquet (nếu có pandas/pyarrow)
    try:
        import pandas as pd
        df = pd.DataFrame(records)
        parquet_path = datalake_dir / "historical_occupancy_30d.parquet"
        df.to_parquet(parquet_path, engine="pyarrow", index=False)
        print(f"[OK] Compressed and saved Apache Parquet file to: {parquet_path}")
    except ImportError:
        print("[INFO] pyarrow/pandas not installed, logs saved in JSON format.")

if __name__ == "__main__":
    generate_historical_logs(30)
