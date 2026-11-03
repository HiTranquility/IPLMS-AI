"""Hệ thống Guardrails phòng hộ 3 rủi ro cốt lõi theo chuẩn Assignment Mục 4.2."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from app.core.copilot.guardrails.text_normalize import normalize_for_match
from app.core.copilot.messages import NO_CONTEXT_ANSWER
from app.util.logger import logger


@dataclass
class GuardrailResult:
    is_safe: bool
    risk_type: Optional[str] = None  # "PROMPT_INJECTION", "OUT_OF_SCOPE", "FAILED_RESPONSE"
    refusal_message: Optional[str] = None
    confidence: float = 0.0


# Các mẫu regex nhận diện tấn công Prompt Injection / Jailbreak
INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b",
    r"(?i)\bforget\s+(all\s+)?(previous|prior)\s+instructions\b",
    r"(?i)\bdisregard\s+(all\s+)?(previous|prior)\s+instructions\b",
    r"(?i)\bsystem\s+prompt\b",
    r"(?i)\breveal\s+(your|the)?\s+(system\s+prompt|secret|password|api\s*key)\b",
    r"(?i)\bshow\s+(me\s+)?(your|the)?\s+(prompt|instructions|system\s+message)\b",
    r"(?i)\bjailbreak\b",
    r"(?i)\bdeveloper\s+mode\b",
    r"(?i)\bact\s+as\s+dan\b",
    r"(?i)\bbỏ\s+qua\s+(hết\s+|mọi\s+|tất\s+cả\s+)?(các\s+|những\s+)?(chỉ\s+dẫn|hướng\s+dẫn|quy\s+tắc)\b",
    r"(?i)\bquên\s+(hết\s+)?(chỉ\s+dẫn|hướng\s+dẫn)\b",
    r"(?i)\btiết\s+lộ\s+(system\s+prompt|mật\s+khẩu|hướng\s+dẫn\s+hệ\s+thống)\b",
    r"(?i)\bđóng\s+vai\s+(hacker|admin|dan)\b",
    r"(?i)\bdrop\s+table\b",
    r"(?i)\bdelete\s+from\b",
]

INJECTION_COMPILED = [re.compile(p) for p in INJECTION_PATTERNS]

# Các mẫu câu hỏi chắc chắn ngoài luồng (Culinary, General Trivia, Creative Writing, Finance/Weather, Personal PII, v.v.)
OUT_OF_SCOPE_PATTERNS = [
    r"(?i)\b(cách\s+nấu|công\s+thức|nấu\s+ăn|nấu\s+phở|cách\s+làm\s+bánh|cách\s+làm\s+món|món\s+ăn|phở\s+bò|bún\s+chả)\b",
    r"(?i)\b(dự\s+báo\s+thời\s+tiết|thời\s+tiết\s+(?:hôm\s+nay|ngày\s+mai)|mưa\s+hay\s+nắng|nhiệt\s+độ\s+ngoài\s+trời)\b",
    r"(?i)\b(thủ\s+đô\s+của|capital\s+of|tổng\s+thống|dân\s+số|diện\s+tích\s+thế\s+giới|chứng\s+khoán|giá\s+vàng|giá\s+bitcoin|tỷ\s+giá|kết\s+quả\s+xổ\s+số)\b",
    r"(?i)\b(thơ\s+tình|viết\s+thơ|làm\s+thơ|bài\s+thơ|sáng\s+tác\s+(?:thơ|nhạc|bài\s+hát)|kể\s+chuyện|viết\s+truyện|viết\s+bài\s+văn|tâm\s+sự|bói\s+toán|viết\s+code|code\s+python|giải\s+phương\s+trình)\b",
    r"(?i)\b(số\s+điện\s+thoại\s+riêng|địa\s+chỉ\s+nhà\s+của\s+giám\s+đốc|lương\s+(?:nhân\s+viên|tháng\s+bao\s+nhiêu)|thông\s+tin\s+cá\s+nhân)\b",
]

OUT_OF_SCOPE_COMPILED = [re.compile(p) for p in OUT_OF_SCOPE_PATTERNS]




class GuardrailManager:
    """Quản lý các rào chắn an toàn (Guardrails) bảo vệ Copilot RAG."""

    def check_input(self, query: str) -> GuardrailResult:
        """Kiểm tra đầu vào người dùng (Rủi ro 1: Prompt Injection, Rủi ro 2: Out-of-scope thô)."""
        clean_q = query.strip()
        if not clean_q:
            return GuardrailResult(
                is_safe=False,
                risk_type="FAILED_RESPONSE",
                refusal_message="Câu hỏi rỗng. Vui lòng nhập nội dung cần tra cứu.",
                confidence=0.0,
            )

        # 1. Kiểm tra Prompt Injection — trên bản chuẩn hoá để ký tự ẩn/Cyrillic không lách được (bug-049)
        # Hai bản: ký tự ẩn bỏ đi (chen giữa chữ) và thành dấu cách (dùng thay dấu cách).
        match_qs = (normalize_for_match(clean_q), normalize_for_match(clean_q, invisible_as=" "))
        for pattern in INJECTION_COMPILED:
            if any(pattern.search(q) for q in match_qs):
                logger.warning("Guardrail kích hoạt: Phát hiện Prompt Injection trong query='%s'", clean_q)
                return GuardrailResult(
                    is_safe=False,
                    risk_type="PROMPT_INJECTION",
                    refusal_message=(
                        "Yêu cầu bị từ chối do vi phạm quy tắc an toàn thông tin của IPLMS AI "
                        "(Phát hiện hành vi Prompt Injection / Can thiệp hệ thống)."
                    ),
                    confidence=0.0,
                )

        # 2. Kiểm tra câu hỏi ngoài phạm vi rõ ràng (trên bản chuẩn hoá NFKC/NFC để chặn NFD & ký tự ẩn — bug-051)
        for pattern in OUT_OF_SCOPE_COMPILED:
            if any(pattern.search(q) for q in match_qs):
                logger.info("Guardrail kích hoạt: Phát hiện câu hỏi ngoài phạm vi query='%s'", clean_q)
                return GuardrailResult(
                    is_safe=False,
                    risk_type="OUT_OF_SCOPE",
                    refusal_message=NO_CONTEXT_ANSWER,
                    confidence=0.0,
                )

        return GuardrailResult(is_safe=True)

    def check_scope_and_chunks(
        self, query: str, chunks: List[dict], min_similarity: float = 0.35
    ) -> GuardrailResult:
        """Kiểm tra ngữ cảnh sau truy xuất (Rủi ro 2: Câu hỏi ngoài phạm vi không có chunk hợp lệ)."""
        if not chunks:
            return GuardrailResult(
                is_safe=False,
                risk_type="OUT_OF_SCOPE",
                refusal_message=NO_CONTEXT_ANSWER,
                confidence=0.0,
            )

        # Đánh giá điểm tương đồng cao nhất
        max_sim = max(float(c.get("similarity", 0.0)) for c in chunks)
        if max_sim < min_similarity:
            logger.info("Guardrail: Độ tương đồng %f < ngưỡng %f -> Từ chối theo ai ADR-0002", max_sim, min_similarity)
            return GuardrailResult(
                is_safe=False,
                risk_type="OUT_OF_SCOPE",
                refusal_message=NO_CONTEXT_ANSWER,
                confidence=0.0,
            )

        return GuardrailResult(is_safe=True)

    def validate_or_fallback_output(
        self, raw_output: Optional[str], chunks: List[dict]
    ) -> Tuple[str, bool]:
        """Kiểm tra đầu ra LLM (Rủi ro 3: Output rỗng, lỗi timeout, suy luận hỏng)."""
        if not raw_output or not raw_output.strip():
            logger.warning("Guardrail: Phát hiện phản hồi LLM rỗng -> Kích hoạt Fallback")
            if chunks:
                top_chunk = chunks[0]
                source = top_chunk.get("source", "quy chế bãi xe")
                fallback = (
                    f"Dịch vụ sinh câu trả lời đang gián đoạn, nội dung tra cứu tương ứng từ tài liệu:\n"
                    f"{top_chunk.get('content', '')}\n[Nguồn: {source}]"
                )
                return fallback, True
            return (
                "Hệ thống trợ lý bãi xe đang bận, vui lòng thử lại sau giây lát hoặc liên hệ nhân viên hỗ trợ.",
                True,
            )

        return raw_output.strip(), False


guardrail_manager = GuardrailManager()
