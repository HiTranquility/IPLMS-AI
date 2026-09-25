"""Nghiệp vụ Dự Báo Lấp Đầy (Occupancy Forecast) & Đề Xuất Giá Động (Dynamic Tariff)."""
from app.core.forecast.dtos.forecast_dto import (
    OccupancyForecast,
    OccupancyForecastQuery,
    TariffRecommendation,
    TariffRecommendationQuery,
)
from app.core.exceptions import FeatureNotImplementedError
from app.util.logger import logger


class ForecastService:
    """[NEVER] bật lại cho tới khi có model dự báo thật.

    Toàn bộ domain này là số học, không phải học máy:

    - ``occupancy_model.predict_occupancy`` (đã xoá 2026-09-25) sinh tỷ lệ bằng
      ``min(0.95, 0.40 + (i * 0.08) % 0.60)`` — một dãy số tăng đều, không đọc
      một dòng lịch sử nào dù có gọi ``parquet_reader``;
    - ``confidence_score`` bị gán cứng ``0.89``;
    - ``get_dynamic_tariff_recommendation`` trả thẳng hệ số ``1.15`` kèm câu
      "Dự báo tỷ lệ lấp đầy đạt 92% vào khung giờ 18:00 - 20:00" cho MỌI bãi,
      mọi thời điểm, mọi mức giá đầu vào.

    Hệ số giá nhân vào tiền khách trả. Một con số bịa ở đây đi thẳng vào hoá đơn,
    và không để lại dấu vết nào trong log lẫn metric — đúng kiểu hỏng mà
    ``FeatureNotImplementedError`` sinh ra để chặn.

    Việc thật cần làm trước khi mở lại: nạp dữ liệu phiên đỗ theo giờ từ datalake,
    train một model dự báo, rồi đo nó trên một tập giữ riêng — giống cách bộ vàng
    đang làm cho ANPR (``data/golden/plates/``).
    """

    @staticmethod
    def get_occupancy_forecast(query: OccupancyForecastQuery) -> OccupancyForecast:
        logger.warning(
            f"ForecastService.GetOccupancyForecast bị gọi cho lot={query.parking_lot_id} "
            f"— chưa có model thật, từ chối thay vì trả dãy số sinh bằng công thức."
        )
        raise FeatureNotImplementedError(
            "Dự báo tỷ lệ lấp đầy chưa khả dụng: chưa có model được huấn luyện "
            "trên dữ liệu phiên đỗ thật."
        )

    @staticmethod
    def get_dynamic_tariff_recommendation(
        query: TariffRecommendationQuery,
    ) -> TariffRecommendation:
        logger.warning(
            f"ForecastService.GetDynamicTariffRecommendation bị gọi cho "
            f"lot={query.parking_lot_id} — chưa có model thật, từ chối thay vì trả "
            f"hệ số giá bịa."
        )
        raise FeatureNotImplementedError(
            "Đề xuất giá động chưa khả dụng: hệ số giá phải dựa trên dự báo thật, "
            "mà phần dự báo chưa được triển khai."
        )


forecast_service = ForecastService()
