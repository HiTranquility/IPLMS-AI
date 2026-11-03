"""Domain Vision — ANPR (nhận diện biển số), phân loại xe, chống gian lận (Pipeline 1)."""
from app.core.vision.dtos.vision_dto import (
    AnprItem,
    PlateResult,
    RecognizePlateCommand,
    VehicleMatchQuery,
    VehicleMatchResult,
)
from app.core.vision.services.anpr_service import AnprService, anpr_service
from app.core.vision.services.anti_fraud_service import AntiFraudService, anti_fraud_service

__all__ = [
    "AnprItem",
    "AnprService",
    "AntiFraudService",
    "PlateResult",
    "RecognizePlateCommand",
    "VehicleMatchQuery",
    "VehicleMatchResult",
    "anpr_service",
    "anti_fraud_service",
]
