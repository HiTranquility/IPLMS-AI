"""LLM-as-judge cho câu `explain` — chỉ chạy SAU khi phần tất định đã qua.

Rubric cố định, không cho câu trả lời được chấm "ra lệnh" cho giám khảo: nội
dung câu trả lời có thể đến từ tài liệu owner tải lên (prompt injection).
"""
from typing import Any, Dict, Tuple

from app.infra.llm.prompts import prompt_store

# Prompt và schema ở `data/prompts/eval_judge/` (ADR-0005).
JUDGE_INSTRUCTIONS = prompt_store.system("eval_judge").text
JUDGE_SCHEMA: Dict[str, Any] = prompt_store.schema("eval_judge")


def build_judge_input(question: str, expected_answer: str, answer: str) -> str:
    return prompt_store.user_template("eval_judge").format(
        question=question, expected_answer=expected_answer, answer=answer
    )


def parse_verdict(payload: Dict[str, Any]) -> Tuple[bool, str]:
    verdict = str(payload.get("verdict", "")).upper()
    reason = str(payload.get("reason", "")).strip()[:200]
    return verdict == "PASS", reason or ("Giám khảo AI chấm đạt." if verdict == "PASS" else "Giám khảo AI chấm trượt.")
