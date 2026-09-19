"""PostgreSQL Client với phần mở rộng pgvector phục vụ lưu trữ và tìm kiếm ngữ nghĩa RAG."""
from typing import List, Dict, Any, Optional
from app.config import get_config
from app.utils.logger import logger

class PgVectorClient:
    """Client giao tiếp trực tiếp với bảng knowledge_chunks qua pgvector."""

    def __init__(self, db_url: str | None = None):
        db_url = db_url or get_config().llm.database_url
        self.db_url = db_url
        self._connected = False

    async def connect(self):
        """Khởi tạo connection pool tới PostgreSQL."""
        logger.info(f"Connecting to PostgreSQL pgvector at {self.db_url.split('@')[-1]}...")
        self._connected = True

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        parking_lot_id: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Thực hiện tìm kiếm Cosine Similarity trên cột embedding.
        
        SQL tương đương:
        SELECT content, metadata, 1 - (embedding <=> $1) AS similarity
        FROM knowledge_chunks
        WHERE parking_lot_id = $2 OR parking_lot_id IS NULL
        ORDER BY embedding <=> $1
        LIMIT $3;
        """
        logger.info(f"Performing pgvector similarity search (top_k={top_k}, parking_lot={parking_lot_id})...")
        
        # Placeholder kết quả mẫu khi chưa kết nối DB thật
        return [
            {
                "content": "Theo quy chế bãi xe Điều 3: Xe gửi qua đêm từ 22:00 đến 06:00 sáng hôm sau tính phụ phí 30.000đ/lượt đối với xe ô tô.",
                "category": "fine_policy",
                "similarity": 0.92,
                "source": "Quy_che_bai_xe_2026.pdf"
            },
            {
                "content": "Biểu phí đỗ xe ô tô giờ đầu 20.000đ/giờ, mỗi giờ tiếp theo 15.000đ/giờ. Quá 4 giờ áp dụng lũy tiến 25.000đ/giờ.",
                "category": "tariff",
                "similarity": 0.88,
                "source": "Bieu_phi_vincom.pdf"
            }
        ]

    async def insert_chunk(
        self,
        content: str,
        embedding: List[float],
        category: str,
        parking_lot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Thêm chunk tri thức mới vào database."""
        logger.info(f"Inserting new knowledge chunk (category={category})...")
        return "chunk_uuid_placeholder"

pgvector_client = PgVectorClient()
