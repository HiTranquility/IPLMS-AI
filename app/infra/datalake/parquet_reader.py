"""Compatibility alias for the historical occupancy reader.

The MVP export is immutable JSONL plus a manifest/checksum so it works without
adding a heavy runtime dependency. A future Parquet adapter can implement the
same interface once the project explicitly approves pyarrow.
"""
from app.infra.datalake.occupancy_reader import OccupancyHistoryReader


ParquetReader = OccupancyHistoryReader
parquet_reader = OccupancyHistoryReader()
