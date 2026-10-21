"""Module đọc dữ liệu Parquet từ Data Lake (MinIO/S3 hoặc local gold layer).

Phục vụ nạp dữ liệu lịch sử lấp đầy (Occupancy Telemetry) để huấn luyện các mô hình
chuỗi thời gian (Prophet / LightGBM) và tích hợp vào ForecastService.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import io
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataLakeError
from app.core.forecast.dtos.forecast_dto import AreaOccupancyTelemetryItem
from app.core.forecast.services.forecast_service import (
    _WEEKDAY_HOURLY_BASELINES,
    _WEEKEND_HOURLY_BASELINES,
)
from app.util.logger import logger


def _resolve_default_gold_lake_path(custom_path: str | Path | None = None) -> Path:
    """Xác định đường dẫn thư mục Parquet Gold Data Lake lưu trữ telemetry lấp đầy."""
    if custom_path:
        return Path(custom_path)

    env_dir = os.environ.get("DATALAKE_DIR") or os.environ.get("AI_DATALAKE_PATH") or os.environ.get("LAKE_LOCAL_FALLBACK_DIR")
    if env_dir:
        cand = Path(env_dir)
        if not cand.is_absolute() and "gold/occupancy" not in str(cand).replace("\\", "/"):
            cand = cand / "gold" / "occupancy"
        if cand.exists():
            return cand

    current_file = Path(__file__).resolve()
    if len(current_file.parents) >= 6:
        repo_root = current_file.parents[5]
        lake_repo = repo_root / "analytic" / "var" / "datalake" / "gold" / "occupancy"
        if lake_repo.exists():
            return lake_repo

    candidates = [
        Path("analytic/var/datalake/gold/occupancy"),
        Path("../analytic/var/datalake/gold/occupancy"),
        Path("var/datalake/gold/occupancy"),
        Path("../var/datalake/gold/occupancy"),
    ]
    for c in candidates:
        if c.exists():
            return c

    return Path("analytic/var/datalake/gold/occupancy")


DEFAULT_GOLD_LAKE_PATH = _resolve_default_gold_lake_path()


def _parse_timestamp(val: Any) -> int:
    """Chuyển đổi các định dạng thời gian khác nhau thành epoch timestamp (giây)."""
    if val is None:
        raise ValueError("Timestamp không được là None")
    if isinstance(val, (int, float)):
        # Nếu là mili-giây (thường > 1e11), chia cho 1000
        if val > 1e11:
            return int(val // 1000)
        return int(val)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        return int(val.astimezone(timezone.utc).timestamp())
    if isinstance(val, str):
        cleaned = val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.astimezone(timezone.utc).timestamp())
    return int(val)


class ParquetLakeReader:
    """Reader đọc và chuẩn hóa dữ liệu Parquet Data Lake cho huấn luyện AI Forecast."""

    def __init__(
        self,
        base_path: str | Path | None = None,
        fallback_area_id: str = "area-central-01",
        fallback_total_slots: int = 100,
    ):
        self.base_path = Path(base_path) if base_path else DEFAULT_GOLD_LAKE_PATH
        self.fallback_area_id = fallback_area_id
        self.fallback_total_slots = max(1, fallback_total_slots)

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

        # 1. Trường hợp không truyền nguồn dữ liệu -> tìm trong local gold lake path
        if file_path_or_buffer is None:
            records = self._read_from_default_path(target_area, fallback_on_error)
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

        # 2. Trường hợp là bytes hoặc buffer rỗng
        if isinstance(file_path_or_buffer, bytes):
            if len(file_path_or_buffer) == 0:
                logger.warning("Buffer Parquet rỗng (0 bytes). Kích hoạt baseline fallback.")
                return self.generate_baseline_telemetry(area_id=target_area)
            source: Any = io.BytesIO(file_path_or_buffer)
        elif isinstance(file_path_or_buffer, io.BytesIO):
            buffer_pos = file_path_or_buffer.tell()
            buffer_bytes = file_path_or_buffer.read()
            file_path_or_buffer.seek(buffer_pos)
            if len(buffer_bytes) == 0:
                logger.warning("BytesIO buffer rỗng. Kích hoạt baseline fallback.")
                return self.generate_baseline_telemetry(area_id=target_area)
            source = file_path_or_buffer
        else:
            # Là str hoặc Path
            path = Path(file_path_or_buffer)
            if not path.exists():
                if fallback_on_error:
                    logger.warning(
                        f"File Parquet '{path}' chưa nạp hoặc không tồn tại. Kích hoạt baseline fallback."
                    )
                    return self.generate_baseline_telemetry(area_id=target_area)
                raise DataLakeError(f"File Parquet '{path}' không tồn tại.")

            if path.is_dir():
                dir_records = self._read_directory(path, target_area, fallback_on_error)
                if area_id is not None:
                    matched = [r for r in dir_records if r["area_id"] == area_id]
                    if matched:
                        return matched
                    if fallback_on_error:
                        logger.warning(
                            f"Không tìm thấy bản ghi cho area_id '{area_id}' trong Parquet Lake directory. Kích hoạt fallback."
                        )
                        return self.generate_baseline_telemetry(area_id=area_id)
                return dir_records

            if path.stat().st_size == 0:
                logger.warning(f"File Parquet '{path}' rỗng (0 bytes). Kích hoạt baseline fallback.")
                return self.generate_baseline_telemetry(area_id=target_area)
            source = path

        # 3. Đọc dữ liệu qua PyArrow
        try:
            table = pq.read_table(source)
        except Exception as exc:
            if fallback_on_error:
                logger.warning(
                    f"Không thể giải mã dữ liệu Parquet ({exc}). Kích hoạt baseline fallback."
                )
                return self.generate_baseline_telemetry(area_id=target_area)
            raise DataLakeError(f"Lỗi đọc file Parquet: {exc}") from exc

        if table.num_rows == 0:
            logger.warning("Bảng Parquet không có dòng dữ liệu nào. Kích hoạt baseline fallback.")
            return self.generate_baseline_telemetry(area_id=target_area)

        raw_records = table.to_pylist()
        normalized = self._normalize_records(raw_records, default_area_id=target_area)

        if not normalized and fallback_on_error:
            logger.warning("Không trích xuất được bản ghi hợp lệ từ Parquet. Kích hoạt fallback.")
            return self.generate_baseline_telemetry(area_id=target_area)

        if area_id is not None:
            matched = [r for r in normalized if r["area_id"] == area_id]
            if matched:
                return matched
            if fallback_on_error:
                logger.warning(
                    f"Không tìm thấy bản ghi cho area_id '{area_id}' trong file Parquet. Kích hoạt fallback."
                )
                return self.generate_baseline_telemetry(area_id=area_id)

        return normalized


    def _read_from_default_path(
        self, area_id: str, fallback_on_error: bool
    ) -> List[Dict[str, Any]]:
        """Đọc từ thư mục mặc định var/datalake/gold/occupancy/."""
        if not self.base_path.exists():
            if fallback_on_error:
                logger.warning(
                    f"Thư mục Data Lake '{self.base_path}' chưa tồn tại. Kích hoạt baseline fallback."
                )
                return self.generate_baseline_telemetry(area_id=area_id)
            raise DataLakeError(f"Thư mục Data Lake '{self.base_path}' không tồn tại.")

        return self._read_directory(self.base_path, area_id, fallback_on_error)

    def _read_directory(
        self, dir_path: Path, area_id: str, fallback_on_error: bool
    ) -> List[Dict[str, Any]]:
        """Đọc và gom các file .parquet trong thư mục."""
        parquet_files = sorted(dir_path.rglob("*.parquet"))
        if not parquet_files:
            if fallback_on_error:
                logger.warning(
                    f"Không tìm thấy file .parquet nào trong '{dir_path}'. Kích hoạt baseline fallback."
                )
                return self.generate_baseline_telemetry(area_id=area_id)
            raise DataLakeError(f"Không có file .parquet trong thư mục '{dir_path}'.")

        all_records: List[Dict[str, Any]] = []
        for file_path in parquet_files:
            if file_path.stat().st_size == 0:
                continue
            try:
                table = pq.read_table(file_path)
                if table.num_rows > 0:
                    records = self._normalize_records(table.to_pylist(), default_area_id=area_id)
                    all_records.extend(records)
            except Exception as exc:
                logger.error(f"Lỗi khi đọc file Parquet con '{file_path}': {exc}")
                if not fallback_on_error:
                    raise DataLakeError(f"Lỗi khi đọc file '{file_path}': {exc}") from exc

        if not all_records:
            return self.generate_baseline_telemetry(area_id=area_id)

        # Loại bỏ bản ghi trùng timestamp theo từng area_id
        unique_map: Dict[tuple[str, int], Dict[str, Any]] = {}
        for r in all_records:
            unique_map[(r["area_id"], r["timestamp"])] = r
        sorted_records = sorted(unique_map.values(), key=lambda x: (x["area_id"], x["timestamp"]))
        return sorted_records

    def _normalize_records(
        self, raw_records: List[Dict[str, Any]], default_area_id: str
    ) -> List[Dict[str, Any]]:
        """Chuẩn hóa cấu trúc bản ghi thành schema thống nhất."""
        normalized: List[Dict[str, Any]] = []

        for row in raw_records:
            # 1. area_id
            area = (
                row.get("area_id")
                or row.get("area_key")
                or row.get("parking_lot_id")
                or row.get("lot_id")
                or default_area_id
            )
            area = str(area).strip()

            # 2. timestamp
            raw_ts = (
                row.get("timestamp")
                or row.get("time")
                or row.get("ts")
                or row.get("datetime")
                or row.get("datetime_iso")
            )
            if raw_ts is None:
                date_actual = row.get("date_actual")
                hour = row.get("hour_of_day", 0)
                if date_actual is not None:
                    try:
                        d_str = str(date_actual).strip()
                        if len(d_str) >= 10 and "-" in d_str:
                            dt_part = d_str[:10]
                            dt_obj = datetime.strptime(dt_part, "%Y-%m-%d").replace(
                                hour=int(hour) % 24, tzinfo=timezone.utc
                            )
                            raw_ts = int(dt_obj.timestamp())
                    except Exception:
                        pass
                elif row.get("date_key") is not None:
                    try:
                        k_str = str(row["date_key"]).strip()
                        if len(k_str) >= 8:
                            dt_obj = datetime(
                                int(k_str[:4]),
                                int(k_str[4:6]),
                                int(k_str[6:8]),
                                int(hour) % 24,
                                tzinfo=timezone.utc,
                            )
                            raw_ts = int(dt_obj.timestamp())
                    except Exception:
                        pass

            if raw_ts is None:
                continue
            try:
                timestamp = _parse_timestamp(raw_ts)
            except (ValueError, TypeError):
                continue

            # 3. total_slots
            raw_total = (
                row.get("total_slots")
                or row.get("capacity")
                or row.get("capacity_at_export")
                or row.get("total_capacity")
                or self.fallback_total_slots
            )
            try:
                total_slots = max(1, int(raw_total))
            except (ValueError, TypeError):
                total_slots = self.fallback_total_slots

            # 4. occupancy_ratio
            raw_ratio = (
                row.get("occupancy_ratio")
                or row.get("avg_occupancy")
                or row.get("occupancy_percent")
                or row.get("avg_occupancy_rate")
                or row.get("peak_occupancy_rate")
            )
            # 5. occupied_slots
            raw_occupied = (
                row.get("occupied_slots")
                or row.get("occupied_equivalent")
                or row.get("occupied_spots")
                or row.get("occupied_count")
            )

            ratio: float
            occupied_slots: int

            if raw_ratio is not None:
                try:
                    ratio = float(raw_ratio)
                    # Nếu tỷ lệ là % (0 - 100), chuẩn hóa về [0.0 - 1.0]
                    if ratio > 1.0:
                        ratio = ratio / 100.0
                    ratio = max(0.0, min(1.0, ratio))
                except (ValueError, TypeError):
                    ratio = 0.0
                if raw_occupied is not None:
                    try:
                        occupied_slots = max(0, int(round(float(raw_occupied))))
                    except (ValueError, TypeError):
                        occupied_slots = int(round(ratio * total_slots))
                else:
                    occupied_slots = int(round(ratio * total_slots))
            elif raw_occupied is not None:
                try:
                    occupied_slots = max(0, int(round(float(raw_occupied))))
                    ratio = min(1.0, max(0.0, occupied_slots / total_slots))
                except (ValueError, TypeError):
                    occupied_slots = 0
                    ratio = 0.0
            else:
                occupied_slots = 0
                ratio = 0.0

            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            normalized.append(
                {
                    "area_id": area,
                    "timestamp": timestamp,
                    "occupied_slots": occupied_slots,
                    "total_slots": total_slots,
                    "occupancy_ratio": round(ratio, 4),
                    "day_of_week": dt.weekday(),
                    "hour_of_day": dt.hour,
                    "datetime_iso": dt.isoformat().replace("+00:00", "Z"),
                    "is_fallback": bool(row.get("is_fallback", False)),
                }
            )

        # Sắp xếp theo timestamp
        normalized.sort(key=lambda r: (r["area_id"], r["timestamp"]))
        return normalized

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
        """Ghi danh sách bản ghi occupancy ra file Parquet hoặc BytesIO buffer.

        Hỗ trợ lưu trữ Gold Layer tại var/datalake/gold/occupancy/ hoặc tải lên S3/MinIO.
        """
        if not records:
            raise ValueError("Không có bản ghi nào để ghi file Parquet.")

        # Chuẩn hóa trường cần thiết thành PyArrow Table
        area_ids = [str(r.get("area_id") or self.fallback_area_id) for r in records]
        timestamps = [_parse_timestamp(r["timestamp"]) for r in records]
        occupied_slots = [int(r.get("occupied_slots", 0)) for r in records]
        total_slots = [int(r.get("total_slots", self.fallback_total_slots)) for r in records]
        occupancy_ratios = [float(r.get("occupancy_ratio", 0.0)) for r in records]

        table = pa.Table.from_pydict(
            {
                "area_id": area_ids,
                "timestamp": timestamps,
                "occupied_slots": occupied_slots,
                "total_slots": total_slots,
                "occupancy_ratio": occupancy_ratios,
            }
        )

        if isinstance(destination, (str, Path)):
            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, dest_path)
        else:
            pq.write_table(table, destination)

        return len(records)

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
