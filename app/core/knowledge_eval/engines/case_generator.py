"""AI đề xuất test case từ chính tài liệu của scope.

Kết quả chỉ là ĐỀ XUẤT: không lưu gì. Người phụ trách duyệt/sửa rồi mới lưu
vào bộ test (SUGGESTION-009 R5) — AI không được tự ra đề rồi tự chấm mà không
có người nhìn.
"""
from typing import Any, Dict, Iterable, List

from app.core.knowledge_eval.engines.grader import KINDS
from app.infra.llm.prompts import prompt_store

# Prompt và schema ở `data/prompts/eval_generator/` (ADR-0005); enum `kind` khớp KINDS (test giữ).
GENERATOR_INSTRUCTIONS = prompt_store.system("eval_generator").text
GENERATOR_SCHEMA: Dict[str, Any] = prompt_store.schema("eval_generator")


def build_generator_input(chunks: Iterable[Dict[str, Any]], max_cases: int) -> str:
    parts = [f"[Nguồn: {chunk['source']}]\n{chunk['content']}" for chunk in chunks]
    return prompt_store.user_template("eval_generator").format(
        max_cases=max_cases, documents="\n\n".join(parts)
    )


def clean_proposals(
    payload: Dict[str, Any], known_sources: Iterable[str], max_cases: int
) -> List[Dict[str, Any]]:
    """Lọc đề xuất của model: bỏ câu rỗng/sai loại, bỏ nguồn không tồn tại, cắt độ dài."""
    sources = set(known_sources)
    cleaned: List[Dict[str, Any]] = []
    seen = set()
    for raw in payload.get("cases") or []:
        question = str(raw.get("question", "")).strip()[:500]
        kind = raw.get("kind")
        if not question or kind not in KINDS or question.lower() in seen:
            continue
        seen.add(question.lower())
        source = str(raw.get("expected_source", "")).strip()
        facts = [str(f).strip()[:100] for f in raw.get("expected_facts") or [] if str(f).strip()]
        cleaned.append(
            {
                "question": question,
                "expected_answer": str(raw.get("expected_answer", "")).strip()[:2000],
                "expected_facts": [] if kind == "abstain" else facts[:10],
                "expected_source": source if source in sources and kind != "abstain" else "",
                "kind": kind,
                "created_by": "ai",
            }
        )
        if len(cleaned) >= max_cases:
            break
    return cleaned
