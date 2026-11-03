"""Administration of task-specific language-model profiles."""
from app.core.model_policy.dtos import ModelProfileDraft

__all__ = ["ModelPolicyService", "ModelProfileDraft", "model_policy_service"]


def __getattr__(name: str):
    if name in ("ModelPolicyService", "model_policy_service"):
        from app.core.model_policy.services import model_policy_service as _mod

        return getattr(_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
