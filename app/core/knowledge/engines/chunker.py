"""Cắt văn bản quy chế thành các đoạn vừa cỡ để sinh embedding.

Vì sao không cắt cứng theo số ký tự: quy chế bãi xe viết theo điều khoản —
"Điều 5 - Quy trình xử lý khiếu nại", "Điều 8 - Xử phạt vi phạm". Cắt cứng sẽ
chặt đôi một điều khoản, để nửa đầu ở đoạn này nửa sau ở đoạn kia. Lúc truy vấn,
cả hai nửa đều trông như câu trả lời dở dang và Copilot sẽ trích thiếu vế.

Nên thuật toán đi hai tầng:
  1. Nhận ra ranh giới điều khoản → mỗi điều khoản là một đoạn trọn vẹn.
  2. Điều khoản nào dài quá ngưỡng thì mới cắt tiếp, ưu tiên ranh giới đoạn văn,
     và các mảnh vẫn mang theo tiêu đề điều khoản của mình.
Không nhận ra cấu trúc nào (file .txt viết liền) thì rơi về tầng 2 cho cả bài.

Module này CỐ Ý không import gì ngoài stdlib: cắt đoạn là thuật toán thuần, test
được mà không cần network, không cần API key, không cần model nào nạp sẵn.
"""
import re
import unicodedata
from typing import List, Optional, Tuple

from app.core.knowledge.constants import CHUNK_MIN_CHARS, CHUNK_OVERLAP_CHARS, CHUNK_TARGET_CHARS
from app.core.knowledge.dtos.knowledge_dto import TextChunk

# Tiêu đề điều khoản tiếng Việt + heading Markdown. Phải đứng riêng một dòng —
# ràng buộc này tránh bắt nhầm chữ "Điều 5" nằm giữa câu văn ("...theo Điều 5 thì...").
_SECTION_PATTERN = re.compile(
    r"^[ \t]*("
    r"(?:Điều|ĐIỀU|Chương|CHƯƠNG|Mục|MỤC|Phần|PHẦN)\s+\d+[^\n]*"
    r"|#{1,6}\s+[^\n]+"
    r")[ \t]*$",
    re.MULTILINE,
)

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


def _normalize(text: str) -> str:
    """Chuẩn hoá xuống dòng và khoảng trắng thừa.

    PDF tách text ra thường kèm khoảng trắng cuối dòng và hàng loạt dòng trống —
    nếu không dọn, chúng ăn vào hạn mức ký tự của đoạn và đẩy nội dung thật ra ngoài.
    PDF còn hay trả chữ Việt ở dạng dấu tách rời (NFD): "phí" thành "phi" + dấu
    sắc, tìm keyword gõ "phí" (NFC) sẽ trượt — nên gộp về NFC.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _hard_split(text: str, target: int, overlap: int) -> List[str]:
    """Cắt cứng theo ký tự — lối thoát cuối khi một đoạn văn dài bất thường.

    Chỉ chạm tới khi cả ranh giới điều khoản lẫn ranh giới đoạn văn đều không
    giúp được (một khối văn bản liền mạch dài hơn ngưỡng). Có overlap để câu bị
    chặt giữa chừng vẫn còn nguyên vẹn ở ít nhất một mảnh.
    """
    step = max(1, target - overlap)
    return [text[i:i + target] for i in range(0, len(text), step)]


def _pack(body: str, target: int, overlap: int) -> List[str]:
    """Gom các đoạn văn lại cho tới sát ngưỡng rồi sang mảnh mới.

    [GOTCHA] `target` là trần CỨNG, và mảnh mới nào cũng phải cõng thêm `overlap`
    ký tự đuôi của mảnh trước. Nên ngân sách cho nội dung mới chỉ còn
    `target - overlap - 2` (2 ký tự cho dấu xuống dòng ngăn cách). Bỏ qua phép
    trừ này thì mảnh nào bắt đầu bằng đuôi overlap cũng vượt trần — và nó vượt
    một cách âm thầm, vì không có gì nổ, chỉ có request embedding to hơn dự tính.
    """
    unit_max = max(1, target - overlap - 2)

    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(body) if p.strip()]
    if not paragraphs:
        return []

    # Nổ trước những đoạn văn tự nó đã vượt ngân sách, nếu không vòng gom bên
    # dưới sẽ nhận nguyên khối đó rồi không bao giờ cắt nhỏ được nữa.
    exploded: List[str] = []
    for para in paragraphs:
        exploded.extend(_hard_split(para, unit_max, 0) if len(para) > unit_max else [para])

    pieces: List[str] = []
    current = ""
    for para in exploded:
        candidate = f"{current}\n\n{para}" if current else para
        if not current or len(candidate) <= target:
            current = candidate
            continue
        pieces.append(current)
        # Mang theo phần đuôi của mảnh trước: câu nằm vắt qua ranh giới vẫn đọc
        # được trọn vẹn ở mảnh sau.
        tail = current[-overlap:] if overlap > 0 else ""
        current = f"{tail}\n\n{para}" if tail else para

    if current:
        pieces.append(current)
    return pieces


def _split_sections(text: str) -> List[Tuple[Optional[str], str]]:
    """Tách theo tiêu đề điều khoản. Trả `[(tiêu đề | None, nội dung)]`.

    Nội dung ĐÃ bao gồm dòng tiêu đề: đoạn văn bản phải tự mang ngữ cảnh của nó.
    Một đoạn ghi "phạt 50.000đ" mà không kèm "Điều 8 - Xử phạt vi phạm" thì lúc
    truy vấn không ai biết 50.000đ đó là phạt cái gì.
    """
    matches = list(_SECTION_PATTERN.finditer(text))
    if not matches:
        return [(None, text)]

    sections: List[Tuple[Optional[str], str]] = []

    head = text[:matches[0].start()].strip()
    if head:
        sections.append((None, head))

    for i, match in enumerate(matches):
        raw_title = match.group(1).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        # Tránh tiêu đề phình to khi OCR thiếu dấu ngắt dòng làm tiêu đề dính cả đoạn văn
        title = raw_title[:200].rsplit(" ", 1)[0] if len(raw_title) > 200 else raw_title
        sections.append((title, f"{raw_title}\n{body}" if body else raw_title))

    return sections


def chunk_text(
    text: str,
    target_chars: int = CHUNK_TARGET_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
    min_chars: int = CHUNK_MIN_CHARS,
) -> List[TextChunk]:
    """Cắt `text` thành danh sách `TextChunk` đánh số thứ tự liên tục từ 0."""
    normalized = _normalize(text)
    if not normalized:
        return []

    chunks: List[TextChunk] = []
    for title, content in _split_sections(normalized):
        pieces = [content] if len(content) <= target_chars else _pack(content, target_chars, overlap_chars)
        for piece in pieces:
            stripped = piece.strip()
            if stripped:
                chunks.append(TextChunk(content=stripped, ordinal=0, section_title=title))

    # Bỏ mảnh quá ngắn (tiêu đề lẻ, dòng sót) — chúng không đủ ngữ cảnh để trả
    # lời nhưng vẫn tốn một lần gọi API embedding và một dòng DB.
    kept = [c for c in chunks if len(c.content) >= min_chars]

    # Trừ khi lọc xong không còn gì: tài liệu ngắn thật (một trang biểu phí) vẫn
    # phải nạp được, thà một đoạn ngắn còn hơn im lặng trả về rỗng.
    if not kept and chunks:
        kept = [max(chunks, key=lambda c: len(c.content))]

    for ordinal, chunk in enumerate(kept):
        chunk.ordinal = ordinal

    return kept
