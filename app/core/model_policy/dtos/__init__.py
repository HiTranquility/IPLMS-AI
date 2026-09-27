"""Model-policy domain data types."""
from typing import TypedDict


class ModelProfileDraft(TypedDict):
    task: str
    provider: str
    model: str
    reasoning_effort: str
    max_output_tokens: int
    timeout_seconds: int
