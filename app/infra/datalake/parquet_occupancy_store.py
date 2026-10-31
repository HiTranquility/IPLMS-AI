"""Đọc/ghi Parquet occupancy ở Gold Data Lake (local hoặc buffer từ MinIO/S3).

Chỉ lo I/O và chuẩn hoá schema bản ghi. Không có dữ liệu → trả `None` (nguồn
rỗng / chưa nạp) hoặc `[]` (có dòng nhưng không dòng nào hợp lệ); quyết định
fallback baseline thuộc `core/forecast/engines/parquet_lake_reader.py`.
"""
from __future__ import annotations

from datetime import datetime, timezone
import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataLakeError
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

    # <IPLMS>/ai/app/infra/datalake/<file> → parents[4] là gốc IPLMS
    current_file = Path(__file__).resolve()
    if len(current_file.parents) >= 5:
        repo_root = current_file.parents[4]
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


class ParquetOccupancyStore:
    """Đọc và chuẩn hoá Parquet occupancy; ghi bản ghi occupancy ra Parquet."""

    def __init__(
        self,
        base_path: str | Path | None = None,
        fallback_area_id: str = "area-central-01",
        fallback_total_slots: int = 100,
    ):
        self.base_path = Path(base_path) if base_path else DEFAULT_GOLD_LAKE_PATH
        self.fallback_area_id = fallback_area_id
        self.fallback_total_slots = max(1, fallback_total_slots)

    def read_records(
        self,
        file_path_or_buffer: str | bytes | Path | io.BytesIO | None = None,
        *,
        default_area_id: str,
        strict: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """Đọc file, thư mục, bytes hoặc BytesIO (None → `base_path`).

        Returns:
            Bản ghi chuẩn hoá; `None` khi nguồn rỗng/chưa có; `[]` khi có dòng
            nhưng không dòng nào hợp lệ.

        Raises:
            DataLakeError: khi `strict` và nguồn thiếu hoặc lỗi giải mã.
        """
        if file_path_or_buffer is None:
            if not self.base_path.exists():
                if not strict:
                    logger.warning(f"Thư mục Data Lake '{self.base_path}' chưa tồn tại.")
                    return None
                raise DataLakeError(f"Thư mục Data Lake '{self.base_path}' không tồn tại.")
            return self._read_directory(self.base_path, default_area_id, strict)

        if isinstance(file_path_or_buffer, bytes):
            if len(file_path_or_buffer) == 0:
                logger.warning("Buffer Parquet rỗng (0 bytes).")
                return None
            source: Any = io.BytesIO(file_path_or_buffer)
        elif isinstance(file_path_or_buffer, io.BytesIO):
            buffer_pos = file_path_or_buffer.tell()
            buffer_bytes = file_path_or_buffer.read()
            file_path_or_buffer.seek(buffer_pos)
            if len(buffer_bytes) == 0:
                logger.warning("BytesIO buffer rỗng.")
                return None
            source = file_path_or_buffer
        else:
            # Là str hoặc Path
            path = Path(file_path_or_buffer)
            if not path.exists():
                if not strict:
                    logger.warning(f"File Parquet '{path}' chưa nạp hoặc không tồn tại.")
                    return None
                raise DataLakeError(f"File Parquet '{path}' không tồn tại.")
            if path.is_dir():
                return self._read_directory(path, default_area_id, strict)
            if path.stat().st_size == 0:
                logger.warning(f"File Parquet '{path}' rỗng (0 bytes).")
                return None
            source = path

        try:
            table = pq.read_table(source)
        except Exception as exc:
            if not strict:
                logger.warning(f"Không thể giải mã dữ liệu Parquet ({exc}).")
                return None
            raise DataLakeError(f"Lỗi đọc file Parquet: {exc}") from exc

        if table.num_rows == 0:
            logger.warning("Bảng Parquet không có dòng dữ liệu nào.")
            return None

        return self._normalize_records(table.to_pylist(), default_area_id=default_area_id)

    def _read_directory(
        self, dir_path: Path, area_id: str, strict: bool
    ) -> Optional[List[Dict[str, Any]]]:
        """Đọc và gom các file .parquet trong thư mục."""
        parquet_files = sorted(dir_path.rglob("*.parquet"))
        if not parquet_files:
            if not strict:
                logger.warning(f"Không tìm thấy file .parquet nào trong '{dir_path}'.")
                return None
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
                if strict:
                    raise DataLakeError(f"Lỗi khi đọc file '{file_path}': {exc}") from exc

        if not all_records:
            return None

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
