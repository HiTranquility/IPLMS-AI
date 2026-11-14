"""Engine dữ liệu huấn luyện Forecast từ Gold Data Lake.

Đọc Parquet qua `app/infra/datalake/parquet_occupancy_store.py`; ở đây chỉ còn
nghiệp vụ: fallback telemetry baseline (7 ngày x 24 giờ), lọc theo `area_id`,
dựng ma trận train (Prophet / LightGBM) và map sang DTO cho ForecastService.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import io
import math
from pathlib import Path
from typing import Any, Dict, List

from app.core.forecast.dtos.forecast_dto import (
    AreaOccupancyTelemetryItem,
    _WEEKDAY_HOURLY_BASELINES,
    _WEEKEND_HOURLY_BASELINES,
)
from app.infra.datalake.parquet_occupancy_store import ParquetOccupancyStore
from app.util.logger import logger


class ParquetLakeReader:
    """Nạp telemetry lấp đầy từ Parquet Data Lake cho huấn luyện AI Forecast."""

    def __init__(
        self,
        base_path: str | Path | None = None,
        fallback_area_id: str = "area-central-01",
        fallback_total_slots: int = 100,
    ):
        self.store = ParquetOccupancyStore(
            base_path=base_path,
            fallback_area_id=fallback_area_id,
            fallback_total_slots=fallback_total_slots,
        )
        self.base_path = self.store.base_path
        self.fallback_area_id = fallback_area_id
        self.fallback_total_slots = self.store.fallback_total_slots

    def read_occupancy_parquet(
        self,
        file_path_or_buffer: str | bytes | Path | io.BytesIO | None = None,
        *,
        area_id: str | None = None,
        fallback_on_error: bool = True,
    ) -> List[Dict[str, Any]]:
        """Đọc file Parquet hoặc buffer từ MinIO/S3 hoặc local storage gold lake.

        Args:
            file_path_or_buffer: Đường dẫn file, thư mục, bytes, BytesIO, hoặc None.
            area_id: Mã bãi/khu vực cần lọc hoặc gán khi fallback.
            fallback_on_error: Nếu True, tự động fallback sang telemetry baseline khi
                               dữ liệu rỗng, chưa nạp hoặc lỗi.

        Returns:
            Danh sách bản ghi chuẩn hóa gồm:
            `area_id`, `timestamp`, `occupied_slots`, `total_slots`, `occupancy_ratio`.
        """
        target_area = area_id or self.fallback_area_id
        records = self.store.read_records(
            file_path_or_buffer, default_area_id=target_area, strict=not fallback_on_error
        )

        # Nguồn rỗng / chưa nạp / lỗi đọc (khi không strict) → baseline
        if records is None:
            logger.warning("Parquet Lake không có dữ liệu dùng được. Kích hoạt baseline fallback.")
            return self.generate_baseline_telemetry(area_id=target_area)

        if not records and fallback_on_error:
            logger.warning("Không trích xuất được bản ghi hợp lệ từ Parquet. Kích hoạt fallback.")
            return self.generate_baseline_telemetry(area_id=target_area)

        if area_id is not None:
            matched = [r for r in records if r["area_id"] == area_id]
            if matched:
                return matched
            if fallback_on_error:
                logger.warning(
                    f"Không tìm thấy bản ghi cho area_id '{area_id}' trong Parquet Lake. Kích hoạt baseline fallback."
                )
                return self.generate_baseline_telemetry(area_id=area_id)

        return records

    def generate_baseline_telemetry(
        self,
        area_id: str | None = None,
        total_slots: int | None = None,
        days: int = 7,
        reference_time: datetime | None = None,
    ) -> List[Dict[str, Any]]:
        """Tự động sinh chuỗi telemetry baseline chuẩn hóa (7 ngày x 24 giờ).

        Dùng làm fallback an toàn khi file Parquet rỗng, chưa nạp hoặc thiếu dữ liệu.
        """
        target_area = area_id or self.fallback_area_id
        capacity = total_slots or self.fallback_total_slots

        # Căn chỉnh mốc bắt đầu về đầu tuần (Thứ 2, 00:00:00 UTC)
        ref = reference_time or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        else:
            ref = ref.astimezone(timezone.utc)

        start_of_day = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = start_of_day - timedelta(days=start_of_day.weekday())

        records: List[Dict[str, Any]] = []
        for d in range(days):
            day_dt = start_of_week + timedelta(days=d)
            dow = day_dt.weekday()
            is_weekend = dow >= 5

            for h in range(24):
                slot_dt = day_dt + timedelta(hours=h)
                ts = int(slot_dt.timestamp())

                # Lấy baseline phần trăm
                if is_weekend:
                    base_pct = _WEEKEND_HOURLY_BASELINES.get(h, 50.0)
                else:
                    base_pct = _WEEKDAY_HOURLY_BASELINES.get(h, 50.0)

                ratio = round(base_pct / 100.0, 4)
                occupied = int(round(capacity * ratio))

                records.append(
                    {
                        "area_id": target_area,
                        "timestamp": ts,
                        "occupied_slots": occupied,
                        "total_slots": capacity,
                        "occupancy_ratio": ratio,
                        "day_of_week": dow,
                        "hour_of_day": h,
                        "datetime_iso": slot_dt.isoformat().replace("+00:00", "Z"),
                        "is_fallback": True,
                        "data_source": "synthetic_fallback",
                    }
                )

        return records

    def filter_training_dataset(
        self, records: List[Dict[str, Any]], min_records: int = 10
    ) -> Dict[str, Any]:
        """Chuẩn bị ma trận train cho mô hình AI chuỗi thời gian (Prophet / LightGBM) chia theo 7 ngày x 24 giờ.

        Args:
            records: Danh sách bản ghi occupancy từ Parquet hoặc telemetry.
            min_records: Ngưỡng tối thiểu số lượng bản ghi hợp lệ.

        Returns:
            Dict chứa ma trận 7x24, dataset định dạng Prophet (`ds`, `y`),
            dataset định dạng LightGBM (`features`, `targets`), và profile tuần.
        """
        is_fallback = False
        working_records = records

        # Kiểm tra ngưỡng dữ liệu tối thiểu
        if not working_records or len(working_records) < min_records:
            logger.warning(
                f"Tập dữ liệu chỉ có {len(working_records) if working_records else 0} bản ghi "
                f"(nhỏ hơn min_records={min_records}). Tự động bổ sung baseline telemetry."
            )
            working_records = self.generate_baseline_telemetry()
            is_fallback = True
        else:
            is_fallback = any(r.get("is_fallback", False) for r in working_records)

        # Gom nhóm theo (day_of_week, hour_of_day)
        ratio_buckets: Dict[tuple[int, int], List[float]] = defaultdict(list)
        slots_buckets: Dict[tuple[int, int], List[int]] = defaultdict(list)

        for r in working_records:
            dow = r.get("day_of_week")
            hour = r.get("hour_of_day")
            if dow is None or hour is None:
                dt = datetime.fromtimestamp(r["timestamp"], tz=timezone.utc)
                dow = dt.weekday()
                hour = dt.hour
            ratio_buckets[(dow, hour)].append(float(r["occupancy_ratio"]))
            slots_buckets[(dow, hour)].append(int(r["occupied_slots"]))

        # Tạo ma trận 7 ngày x 24 giờ (7 hàng, 24 cột)
        matrix_7x24: List[List[float]] = []
        slots_matrix_7x24: List[List[int]] = []

        for dow in range(7):
            row_ratio: List[float] = []
            row_slots: List[int] = []
            for hour in range(24):
                vals = ratio_buckets.get((dow, hour))
                if vals:
                    mean_ratio = round(sum(vals) / len(vals), 4)
                    mean_slots = int(round(sum(slots_buckets[(dow, hour)]) / len(vals)))
                else:
                    # Điền baseline nếu slot thiếu
                    is_weekend = dow >= 5
                    base_pct = (
                        _WEEKEND_HOURLY_BASELINES.get(hour, 50.0)
                        if is_weekend
                        else _WEEKDAY_HOURLY_BASELINES.get(hour, 50.0)
                    )
                    mean_ratio = round(base_pct / 100.0, 4)
                    mean_slots = int(round(self.fallback_total_slots * mean_ratio))
                row_ratio.append(mean_ratio)
                row_slots.append(mean_slots)
            matrix_7x24.append(row_ratio)
            slots_matrix_7x24.append(row_slots)

        # Thống kê Weekly Profile
        weekday_ratios = [matrix_7x24[d][h] for d in range(5) for h in range(24)]
        weekend_ratios = [matrix_7x24[d][h] for d in range(5, 7) for h in range(24)]
        all_ratios = weekday_ratios + weekend_ratios

        weekday_mean = round(sum(weekday_ratios) / len(weekday_ratios), 4) if weekday_ratios else 0.0
        weekend_mean = round(sum(weekend_ratios) / len(weekend_ratios), 4) if weekend_ratios else 0.0
        overall_mean = round(sum(all_ratios) / len(all_ratios), 4) if all_ratios else 0.0

        # Tìm giờ cao điểm (Peak) và thấp điểm (Off-peak)
        peak_ratio = -1.0
        peak_slot = (0, 0)
        off_peak_ratio = 2.0
        off_peak_slot = (0, 0)
        for d in range(7):
            for h in range(24):
                r_val = matrix_7x24[d][h]
                if r_val > peak_ratio:
                    peak_ratio = r_val
                    peak_slot = (d, h)
                if r_val < off_peak_ratio:
                    off_peak_ratio = r_val
                    off_peak_slot = (d, h)

        weekly_profile = {
            "weekday_mean": weekday_mean,
            "weekend_mean": weekend_mean,
            "overall_mean": overall_mean,
            "peak_day_of_week": peak_slot[0],
            "peak_hour": peak_slot[1],
            "peak_ratio": peak_ratio,
            "off_peak_day_of_week": off_peak_slot[0],
            "off_peak_hour": off_peak_slot[1],
            "off_peak_ratio": off_peak_ratio,
        }

        # Format dataset chuẩn cho Prophet: {"ds": str, "y": float}
        sorted_records = sorted(working_records, key=lambda x: x["timestamp"])
        prophet_dataset = [
            {
                "ds": r.get("datetime_iso")
                or datetime.fromtimestamp(r["timestamp"], tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "y": float(r["occupancy_ratio"]),
            }
            for r in sorted_records
        ]

        # Format dataset chuẩn cho LightGBM: Features X và Target y
        # Features chu kỳ thời gian: day_of_week, hour_of_day, is_weekend, total_slots,
        # sin/cos biến đổi chu kỳ để cây học được liên tục thời gian
        lightgbm_features: List[List[float]] = []
        lightgbm_targets: List[float] = []
        feature_names = [
            "day_of_week",
            "hour_of_day",
            "is_weekend",
            "total_slots",
            "hour_sin",
            "hour_cos",
            "dow_sin",
            "dow_cos",
        ]

        for r in sorted_records:
            dow = int(r.get("day_of_week", 0))
            hour = int(r.get("hour_of_day", 0))
            is_wk = 1.0 if dow >= 5 else 0.0
            slots = float(r.get("total_slots", 100))

            h_sin = round(math.sin(2 * math.pi * hour / 24.0), 6)
            h_cos = round(math.cos(2 * math.pi * hour / 24.0), 6)
            d_sin = round(math.sin(2 * math.pi * dow / 7.0), 6)
            d_cos = round(math.cos(2 * math.pi * dow / 7.0), 6)

            feat = [float(dow), float(hour), is_wk, slots, h_sin, h_cos, d_sin, d_cos]
            lightgbm_features.append(feat)
            lightgbm_targets.append(float(r["occupancy_ratio"]))

        # Lấy danh sách area_id duy nhất
        area_ids = sorted(list({str(r["area_id"]) for r in working_records if "area_id" in r}))

        return {
            "area_ids": area_ids,
            "total_records": len(working_records),
            "min_records": min_records,
            "is_fallback": is_fallback,
            "matrix_7x24": matrix_7x24,
            "slots_matrix_7x24": slots_matrix_7x24,
            "weekly_profile": weekly_profile,
            "prophet_dataset": prophet_dataset,
            "lightgbm_dataset": {
                "features": lightgbm_features,
                "targets": lightgbm_targets,
                "feature_names": feature_names,
            },
        }

    def write_occupancy_parquet(
        self, records: List[Dict[str, Any]], destination: str | Path | io.BytesIO
    ) -> int:
        """Ghi bản ghi occupancy ra Parquet — uỷ cho `ParquetOccupancyStore`."""
        return self.store.write_occupancy_parquet(records, destination)

    def to_telemetry_items(self, records: List[Dict[str, Any]]) -> List[AreaOccupancyTelemetryItem]:
        """Chuyển đổi danh sách bản ghi occupancy thành danh sách DTO AreaOccupancyTelemetryItem.

        Tạo cầu nối trực tiếp để nạp vào ForecastService.ingest_telemetry().
        """
        items: List[AreaOccupancyTelemetryItem] = []
        for r in records:
            dow = r.get("day_of_week")
            hour = r.get("hour_of_day")
            if dow is None or hour is None:
                dt = datetime.fromtimestamp(r["timestamp"], tz=timezone.utc)
                dow = dt.weekday()
                hour = dt.hour

            items.append(
                AreaOccupancyTelemetryItem(
                    area_id=r["area_id"],
                    day_of_week=dow,
                    hour_of_day=hour,
                    avg_occupancy_ratio=r["occupancy_ratio"],
                    total_capacity=r.get("total_slots", 100),
                    sample_count=1,
                )
            )
        return items


parquet_lake_reader = ParquetLakeReader()
