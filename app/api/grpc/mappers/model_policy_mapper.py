"""Translate model profile DTOs to protobuf without exposing credentials."""
from typing import Any

from app.api.grpc.generated_stubs import get_stub

_pb2, _ = get_stub("model_policy_service")


def to_model_profile_response(profile: dict[str, Any]) -> Any:
    return _pb2.ModelProfile(**profile)


def to_create_profile_command(request: Any) -> dict[str, Any]:
    return {
        "task": request.task, "provider": request.provider, "model": request.model,
        "reasoning_effort": request.reasoning_effort or "none",
        "max_output_tokens": request.max_output_tokens,
        "timeout_seconds": request.timeout_seconds,
    }
