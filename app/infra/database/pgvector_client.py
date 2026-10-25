"""Real PostgreSQL/pgvector adapter for the Copilot knowledge base."""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4
from typing import Any, Dict, List, Optional

from app.config import get_config
from app.infra.database.db_connection import connect_with_fallback
from app.core.exceptions import RagPipelineError
from app.infra.database.keyword_search import FOLDED_CONTENT_TSVECTOR, build_keyword_tsquery
from app.util.logger import logger


class PgVectorClient:
    """Blocking psycopg2 calls isolated behind ``asyncio.to_thread``."""

    def __init__(self, db_url: str | None = None):
        config = get_config()
        self.db_url = db_url or config.llm.database_url
        self.dimensions = config.embedding.dimensions
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()
        self._has_pgvector = True

    def _connect_sync(self, register: bool = True):
        if not self.db_url:
            raise RagPipelineError("Thiếu AI_DATABASE_URL cho kho tri thức.")
        try:
            connection, self.db_url = connect_with_fallback(
                self.db_url, connect_timeout=3, register_vector=(register and self._has_pgvector)
            )
            return connection
        except Exception as exc:
            raise RagPipelineError("Không kết nối được PostgreSQL/pgvector.") from exc

    async def connect(self) -> None:
        await self.ensure_schema()

    async def get_knowledge_stats(self) -> Dict[str, int]:
        """Return cheap readiness counters without exposing document content."""
        await self.ensure_schema()
        return await asyncio.to_thread(self._get_knowledge_stats_sync)

    def _get_knowledge_stats_sync(self) -> Dict[str, int]:
        connection = self._connect_sync()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM knowledge_documents),
                        (SELECT COUNT(*) FROM knowledge_chunks),
                        (SELECT COUNT(*) FROM knowledge_chunks WHERE parking_lot_id IS NULL)
                    """
                )
                documents, chunks, global_chunks = cursor.fetchone()
                return {
                    "documents": int(documents),
                    "chunks": int(chunks),
                    "global_chunks": int(global_chunks),
                }
        except Exception as exc:
            raise RagPipelineError("Không đọc được trạng thái kho tri thức.") from exc
        finally:
            connection.close()

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await asyncio.to_thread(self._ensure_schema_sync)
            self._schema_ready = True

    def _ensure_schema_sync(self) -> None:
        if not 1 <= self.dimensions <= 65535:
            raise RagPipelineError("AI_EMBEDDING_DIMENSIONS không hợp lệ.")
        # pgvector's adapter can only be registered after the extension exists.
        connection = self._connect_sync(register=False)
        try:
            with connection:
                with connection.cursor() as cursor:
                    # 2 replica cùng khởi động cùng chạy khối này: khoá để DDL/backfill
                    # chạy tuần tự, tránh lỗi trùng khoá khi cả hai cùng INSERT.
                    cursor.execute("SELECT pg_advisory_xact_lock(724100)")
                    cursor.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
                    self._has_pgvector = cursor.fetchone() is not None
                    if self._has_pgvector:
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        from pgvector.psycopg2 import register_vector

                        register_vector(connection)
                        embedding_col_type = f"vector({self.dimensions})"
                    else:
                        embedding_col_type = "DOUBLE PRECISION[]"
                        cursor.execute(
                            """
                            CREATE OR REPLACE FUNCTION iplms_cosine_sim(a DOUBLE PRECISION[], b DOUBLE PRECISION[])
                            RETURNS DOUBLE PRECISION
                            LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
                                SELECT CASE
                                    WHEN a IS NULL OR b IS NULL THEN 0.0
                                    ELSE COALESCE(
                                        SUM(x * y) / NULLIF(SQRT(SUM(x * x)) * SQRT(SUM(y * y)), 0.0),
                                        0.0
                                    )
                                END
                                FROM unnest(a, b) AS t(x, y);
                            $$
                            """
                        )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS knowledge_documents (
                            id UUID PRIMARY KEY,
                            parking_lot_id VARCHAR(100),
                            file_name VARCHAR(255) NOT NULL,
                            category VARCHAR(50) NOT NULL,
                            uploaded_by VARCHAR(100),
                            status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
                            chunk_count INTEGER NOT NULL DEFAULT 0,
                            message TEXT NOT NULL DEFAULT '',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cursor.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS knowledge_chunks (
                            id UUID PRIMARY KEY,
                            document_id UUID CONSTRAINT fk_knowledge_chunks_document
                                REFERENCES knowledge_documents(id) ON DELETE CASCADE,
                            parking_lot_id VARCHAR(100),
                            category VARCHAR(50) NOT NULL,
                            title VARCHAR(255),
                            content TEXT NOT NULL,
                            source VARCHAR(255) NOT NULL,
                            ordinal INTEGER NOT NULL DEFAULT 0,
                            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                            embedding {embedding_col_type} NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    # Upgrade the legacy seed table without deleting its rows.
                    cursor.execute(
                        """
                        ALTER TABLE knowledge_chunks
                            ADD COLUMN IF NOT EXISTS document_id UUID,
                            ADD COLUMN IF NOT EXISTS ordinal INTEGER NOT NULL DEFAULT 0
                        """
                    )
                    cursor.execute(
                        """
                        DO $$ BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint
                                WHERE conname = 'fk_knowledge_chunks_document'
                            ) THEN
                                ALTER TABLE knowledge_chunks
                                ADD CONSTRAINT fk_knowledge_chunks_document
                                FOREIGN KEY (document_id)
                                REFERENCES knowledge_documents(id)
                                ON DELETE CASCADE NOT VALID;
                            END IF;
                        END $$
                        """
                    )
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_scope_category
                        ON knowledge_chunks (parking_lot_id, category)
                        """
                    )
                    if self._has_pgvector:
                        cursor.execute(
                            """
                            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding_hnsw
                            ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
                            WHERE embedding IS NOT NULL
                            """
                        )
                    # Index cũ (có dấu) không còn câu truy vấn nào dùng; giữ lại chỉ
                    # tốn chi phí ghi mỗi lần nạp chunk.
                    cursor.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_content_fts")
                    cursor.execute(
                        f"""
                        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_content_folded_fts
                        ON knowledge_chunks USING gin ({FOLDED_CONTENT_TSVECTOR})
                        """
                    )
                    self._ensure_version_schema(cursor)
        except RagPipelineError:
            raise
        except Exception as exc:
            raise RagPipelineError("Không khởi tạo được schema pgvector.") from exc
        finally:
            connection.close()

    @staticmethod
    def _ensure_version_schema(cursor) -> None:
        """Phiên bản tài liệu (ISSUE-009 phase 1).

        Mỗi tài liệu: tối đa 1 bản nháp (DRAFT/TESTED) và tối đa 1 bản PUBLISHED —
        ép bằng unique index một phần, không dựa vào code nhớ kiểm.
        """
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_document_versions (
                id UUID PRIMARY KEY,
                document_id UUID NOT NULL
                    REFERENCES knowledge_documents(id) ON DELETE CASCADE,
                version_no INTEGER NOT NULL,
                status VARCHAR(16) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                uploaded_by VARCHAR(100),
                chunk_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                published_at TIMESTAMPTZ,
                published_by VARCHAR(100),
                CONSTRAINT uq_knowledge_versions_no UNIQUE (document_id, version_no),
                CONSTRAINT ck_knowledge_versions_status
                    CHECK (status IN ('DRAFT', 'TESTED', 'PUBLISHED', 'ARCHIVED'))
            )
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_versions_one_published
            ON knowledge_document_versions (document_id) WHERE status = 'PUBLISHED'
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_versions_one_draft
            ON knowledge_document_versions (document_id) WHERE status IN ('DRAFT', 'TESTED')
            """
        )
        cursor.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS version_id UUID")
        cursor.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_knowledge_chunks_version'
                ) THEN
                    ALTER TABLE knowledge_chunks
                    ADD CONSTRAINT fk_knowledge_chunks_version
                    FOREIGN KEY (version_id)
                    REFERENCES knowledge_document_versions(id) ON DELETE CASCADE NOT VALID;
                END IF;
            END $$
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_version ON knowledge_chunks (version_id)"
        )
        # Tài liệu nạp TRƯỚC khi có phiên bản đang phục vụ khách → giữ nguyên là
        # v1 PUBLISHED (id phiên bản = id tài liệu), Copilot không "mất trí nhớ".
        cursor.execute(
            """
            INSERT INTO knowledge_document_versions
                (id, document_id, version_no, status, file_name, uploaded_by,
                 chunk_count, created_at, published_at, published_by)
            SELECT d.id, d.id, 1, 'PUBLISHED', d.file_name, d.uploaded_by,
                   d.chunk_count, d.created_at, d.updated_at, 'migration'
            FROM knowledge_documents d
            WHERE NOT EXISTS (
                SELECT 1 FROM knowledge_document_versions v WHERE v.document_id = d.id
            )
            ON CONFLICT DO NOTHING
            """
        )
        cursor.execute(
            """
            UPDATE knowledge_chunks c SET version_id = c.document_id
            WHERE c.version_id IS NULL AND c.document_id IS NOT NULL
              AND EXISTS (SELECT 1 FROM knowledge_document_versions v WHERE v.id = c.document_id)
            """
        )

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        query_text: str,
        parking_lot_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.35,
        preview: bool = False,
    ) -> List[Dict[str, Any]]:
        """`preview=False`: đúng thứ khách thấy (chỉ bản PUBLISHED).

        `preview=True`: bản xem trước của scope `parking_lot_id` (None = tài liệu
        chung) — bản mới nhất chưa lưu trữ của scope đó + bản PUBLISHED của phần
        còn lại. Dùng cho "Hỏi thử" và lượt chạy test (ISSUE-009).
        """
        if len(query_embedding) != self.dimensions:
            raise RagPipelineError(
                "Số chiều query embedding không khớp schema knowledge_chunks."
            )
        await self.ensure_schema()
        return await asyncio.to_thread(
            self._search_sync,
            query_embedding,
            query_text,
            parking_lot_id,
            max(1, min(top_k, 20)),
            max(-1.0, min(min_similarity, 1.0)),
            preview,
        )

    @staticmethod
    def _visible_versions_sql(preview: bool) -> str:
        if not preview:
            return "SELECT id FROM knowledge_document_versions WHERE status = 'PUBLISHED'"
        return """
            SELECT id FROM (
                SELECT DISTINCT ON (v.document_id) v.id
                FROM knowledge_document_versions v
                JOIN knowledge_documents d ON d.id = v.document_id
                WHERE v.status <> 'ARCHIVED'
                  AND d.parking_lot_id IS NOT DISTINCT FROM %(preview_scope)s
                ORDER BY v.document_id, v.version_no DESC
            ) latest
            UNION ALL
            SELECT v.id FROM knowledge_document_versions v
            JOIN knowledge_documents d ON d.id = v.document_id
            WHERE v.status = 'PUBLISHED'
              AND d.parking_lot_id IS DISTINCT FROM %(preview_scope)s
        """

    def _search_sync(
        self,
        query_embedding: List[float],
        query_text: str,
        parking_lot_id: Optional[str],
        top_k: int,
        min_similarity: float,
        preview: bool = False,
    ) -> List[Dict[str, Any]]:
        connection = self._connect_sync()
        try:
            with connection.cursor() as cursor:
                # Không có bãi → chỉ tài liệu chung; nếu không sẽ lộ quy chế riêng
                # của owner khác.
                scope_sql = (
                    "(parking_lot_id = %(lot)s OR parking_lot_id IS NULL)"
                    if parking_lot_id
                    else "parking_lot_id IS NULL"
                )
                params: Dict[str, Any] = {
                    "q": build_keyword_tsquery(query_text),
                    "emb": query_embedding,
                    "lot": parking_lot_id,
                    "min_sim": min_similarity,
                    "cand": min(80, max(20, top_k * 4)),
                    "top_k": top_k,
                    "preview_scope": parking_lot_id,
                }
                sim_expr = (
                    "1 - (embedding <=> %(emb)s::vector)"
                    if self._has_pgvector
                    else "iplms_cosine_sim(embedding, %(emb)s::double precision[])"
                )
                fused_sim_expr = (
                    "1 - (kc_emb.embedding <=> %(emb)s::vector)"
                    if self._has_pgvector
                    else "iplms_cosine_sim(kc_emb.embedding, %(emb)s::double precision[])"
                )
                cursor.execute(
                    f"""
                    WITH visible AS ({self._visible_versions_sql(preview)}),
                    search_query AS (
                        SELECT to_tsquery('simple', %(q)s) AS value
                    ),
                    scoped AS NOT MATERIALIZED (
                        SELECT * FROM knowledge_chunks
                        WHERE {scope_sql} AND version_id IN (SELECT id FROM visible)
                    ),
                    vector_candidates AS (
                        SELECT id, similarity,
                               ROW_NUMBER() OVER (ORDER BY similarity DESC) AS rank
                        FROM (
                            SELECT id, {sim_expr} AS similarity
                            FROM scoped WHERE embedding IS NOT NULL
                        ) scored
                        WHERE similarity >= %(min_sim)s
                        ORDER BY similarity DESC
                        LIMIT %(cand)s
                    ),
                    keyword_candidates AS (
                        SELECT kc.id,
                               ROW_NUMBER() OVER (
                                   ORDER BY ts_rank_cd(kc.folded, sq.value) DESC
                               ) AS rank
                        FROM (
                            SELECT id, {FOLDED_CONTENT_TSVECTOR} AS folded FROM scoped
                        ) kc
                        CROSS JOIN search_query sq
                        WHERE kc.folded @@ sq.value
                        ORDER BY ts_rank_cd(kc.folded, sq.value) DESC
                        LIMIT %(cand)s
                    ),
                    fused AS (
                        SELECT COALESCE(v.id, kw.id) AS id,
                               COALESCE(v.similarity, {fused_sim_expr}, 0.0) AS similarity,
                               COALESCE(1.0 / (60 + v.rank), 0.0)
                                 + COALESCE(1.0 / (60 + kw.rank), 0.0) AS hybrid_score
                        FROM vector_candidates v
                        FULL OUTER JOIN keyword_candidates kw ON kw.id = v.id
                        LEFT JOIN scoped kc_emb ON kc_emb.id = COALESCE(v.id, kw.id)
                    )
                    SELECT kc.content, kc.category, fused.similarity,
                           kc.source, kc.metadata, kc.document_id::text, kc.ordinal,
                           fused.hybrid_score
                    FROM fused
                    JOIN knowledge_chunks kc ON kc.id = fused.id
                    ORDER BY fused.hybrid_score DESC
                    LIMIT %(top_k)s
                    """,
                    params,
                )
                return [
                    {
                        "content": row[0],
                        "category": row[1],
                        "similarity": float(row[2]),
                        "source": row[3],
                        "metadata": row[4] or {},
                        "document_id": row[5],
                        "ordinal": row[6],
                        "hybrid_score": float(row[7]),
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as exc:
            raise RagPipelineError("Truy vấn similarity trên pgvector thất bại.") from exc
        finally:
            connection.close()

    async def save_draft_version(
        self,
        *,
        document_id: str,
        file_name: str,
        category: str,
        parking_lot_id: Optional[str],
        uploaded_by: Optional[str],
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Ghi một bản NHÁP cho tài liệu, trong một transaction.

        Tài liệu đang có nháp → thay nháp đó tại chỗ (mỗi tài liệu tối đa 1 nháp);
        chưa có → tạo phiên bản mới `max+1`. Bản PUBLISHED hiện tại KHÔNG bị đụng:
        khách vẫn thấy nó tới lúc scope được xuất bản lại.
        """
        await self.ensure_schema()
        return await asyncio.to_thread(
            self._save_draft_version_sync,
            document_id,
            file_name,
            category,
            parking_lot_id,
            uploaded_by,
            chunks,
        )

    def _save_draft_version_sync(
        self,
        document_id: str,
        file_name: str,
        category: str,
        parking_lot_id: Optional[str],
        uploaded_by: Optional[str],
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        connection = self._connect_sync()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO knowledge_documents
                            (id, parking_lot_id, file_name, category, uploaded_by, status, chunk_count)
                        VALUES (%s, %s, %s, %s, %s, 'SUCCESS', %s)
                        ON CONFLICT (id) DO UPDATE SET
                            file_name = EXCLUDED.file_name,
                            category = EXCLUDED.category,
                            uploaded_by = EXCLUDED.uploaded_by,
                            chunk_count = EXCLUDED.chunk_count,
                            updated_at = NOW()
                        WHERE knowledge_documents.parking_lot_id
                              IS NOT DISTINCT FROM EXCLUDED.parking_lot_id
                        RETURNING id
                        """,
                        (document_id, parking_lot_id, file_name, category, uploaded_by, len(chunks)),
                    )
                    if cursor.fetchone() is None:
                        # Cùng document_id nhưng khác bãi: không cho "chuyển" tài liệu
                        # sang scope khác qua đường nạp lại.
                        raise ValueError("Tài liệu này thuộc phạm vi khác, không nạp lại được.")
                    cursor.execute(
                        """
                        SELECT id, version_no FROM knowledge_document_versions
                        WHERE document_id = %s AND status IN ('DRAFT', 'TESTED')
                        FOR UPDATE
                        """,
                        (document_id,),
                    )
                    draft = cursor.fetchone()
                    if draft:
                        previous_version_id, version_no = str(draft[0]), int(draft[1])
                        version_id = str(uuid4())
                        cursor.execute("DELETE FROM knowledge_chunks WHERE version_id = %s", (previous_version_id,))
                        cursor.execute(
                            """
                            UPDATE knowledge_document_versions
                            SET id = %s, status = 'DRAFT', file_name = %s, uploaded_by = %s,
                                chunk_count = %s, created_at = NOW()
                            WHERE id = %s
                            """,
                            (version_id, file_name, uploaded_by, len(chunks), previous_version_id),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT COALESCE(MAX(version_no), 0) + 1
                            FROM knowledge_document_versions WHERE document_id = %s
                            """,
                            (document_id,),
                        )
                        version_no = int(cursor.fetchone()[0])
                        version_id = str(uuid4())
                        cursor.execute(
                            """
                            INSERT INTO knowledge_document_versions
                                (id, document_id, version_no, status, file_name, uploaded_by, chunk_count)
                            VALUES (%s, %s, %s, 'DRAFT', %s, %s, %s)
                            """,
                            (version_id, document_id, version_no, file_name, uploaded_by, len(chunks)),
                        )
                    for chunk in chunks:
                        cursor.execute(
                            """
                            INSERT INTO knowledge_chunks
                                (id, document_id, version_id, parking_lot_id, category, title,
                                 content, source, ordinal, metadata, embedding)
                            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                document_id,
                                version_id,
                                parking_lot_id,
                                category,
                                chunk.get("section_title") or file_name,
                                chunk["content"],
                                file_name,
                                chunk["ordinal"],
                                json.dumps(chunk.get("metadata") or {}),
                                chunk["embedding"],
                            ),
                        )
                    return {"version_id": version_id, "version_no": version_no}
        except ValueError:
            raise
        except Exception as exc:
            connection.rollback()
            raise RagPipelineError("Không ghi được tài liệu vào pgvector; đã rollback.") from exc
        finally:
            connection.close()

    async def publish_versions(
        self, parking_lot_id: Optional[str], version_ids: List[str], published_by: str
    ) -> int:
        """Đưa các bản nháp lên PUBLISHED, lưu trữ bản PUBLISHED cũ — một transaction.

        Chỉ nhận phiên bản thuộc đúng scope và đang DRAFT/TESTED. Cổng kiểm thử
        (R3/R4) nằm ở tầng gọi; hàm này chỉ đảm bảo không có khoảnh khắc nào
        một tài liệu có 0 hoặc 2 bản PUBLISHED.
        """
        await self.ensure_schema()
        return await asyncio.to_thread(
            self._publish_versions_sync, parking_lot_id, version_ids, published_by
        )

    def _publish_versions_sync(
        self, parking_lot_id: Optional[str], version_ids: List[str], published_by: str
    ) -> int:
        if not version_ids:
            return 0
        connection = self._connect_sync()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT v.id::text, v.document_id::text
                        FROM knowledge_document_versions v
                        JOIN knowledge_documents d ON d.id = v.document_id
                        WHERE v.id = ANY(%s::uuid[]) AND v.status IN ('DRAFT', 'TESTED')
                          AND d.parking_lot_id IS NOT DISTINCT FROM %s
                        FOR UPDATE OF v
                        """,
                        (list(version_ids), parking_lot_id),
                    )
                    rows = cursor.fetchall()
                    if len(rows) != len(set(version_ids)):
                        raise RagPipelineError(
                            "Tập phiên bản xuất bản đã thay đổi; không xuất bản một phần."
                        )
                    for version_id, document_id in rows:
                        cursor.execute(
                            """
                            UPDATE knowledge_document_versions SET status = 'ARCHIVED'
                            WHERE document_id = %s AND status = 'PUBLISHED'
                            """,
                            (document_id,),
                        )
                        cursor.execute(
                            """
                            UPDATE knowledge_document_versions
                            SET status = 'PUBLISHED', published_at = NOW(), published_by = %s
                            WHERE id = %s
                            """,
                            (published_by, version_id),
                        )
                    return len(rows)
        except Exception as exc:
            raise RagPipelineError("Không xuất bản được tài liệu; đã rollback.") from exc
        finally:
            connection.close()

    async def latest_version_ids(self, parking_lot_id: Optional[str]) -> List[str]:
        """Phiên bản mới nhất (chưa lưu trữ) của từng tài liệu trong scope."""
        await self.ensure_schema()
        return await asyncio.to_thread(self._latest_version_ids_sync, parking_lot_id)

    def _latest_version_ids_sync(self, parking_lot_id: Optional[str]) -> List[str]:
        connection = self._connect_sync()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT ON (v.document_id) v.id::text
                    FROM knowledge_document_versions v
                    JOIN knowledge_documents d ON d.id = v.document_id
                    WHERE v.status <> 'ARCHIVED'
                      AND d.parking_lot_id IS NOT DISTINCT FROM %s
                    ORDER BY v.document_id, v.version_no DESC
                    """,
                    (parking_lot_id,),
                )
                return sorted(row[0] for row in cursor.fetchall())
        except Exception as exc:
            raise RagPipelineError("Không đọc được phiên bản tài liệu.") from exc
        finally:
            connection.close()

    async def mark_versions_tested(self, version_ids: List[str], tested: bool) -> None:
        """Lượt chạy đạt → DRAFT thành TESTED; trượt → TESTED về DRAFT."""
        await self.ensure_schema()
        await asyncio.to_thread(self._mark_versions_tested_sync, version_ids, tested)

    def _mark_versions_tested_sync(self, version_ids: List[str], tested: bool) -> None:
        if not version_ids:
            return
        source, target = ("DRAFT", "TESTED") if tested else ("TESTED", "DRAFT")
        connection = self._connect_sync()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE knowledge_document_versions SET status = %s
                        WHERE id = ANY(%s::uuid[]) AND status = %s
                        """,
                        (target, list(version_ids), source),
                    )
        except Exception as exc:
            raise RagPipelineError("Không cập nhật được trạng thái phiên bản.") from exc
        finally:
            connection.close()

    async def list_documents(self, parking_lot_id: Optional[str]) -> List[Dict[str, Any]]:
        await self.ensure_schema()
        return await asyncio.to_thread(self._list_documents_sync, parking_lot_id)

    async def list_document_chunks(
        self, document_id: str, parking_lot_id: Optional[str], version_no: int = 0
    ) -> Dict[str, Any]:
        """Đọc tối đa 100 đoạn của một phiên bản; ràng buộc scope ngay tại SQL."""
        if version_no < 0:
            raise ValueError("Số phiên bản phải lớn hơn 0.")
        await self.ensure_schema()
        return await asyncio.to_thread(
            self._list_document_chunks_sync, document_id, parking_lot_id, version_no
        )

    def _list_document_chunks_sync(
        self, document_id: str, parking_lot_id: Optional[str], version_no: int = 0
    ) -> Dict[str, Any]:
        connection = self._connect_sync()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT v.version_no, v.status, v.chunk_count, v.created_at,
                           v.published_at
                    FROM knowledge_documents d
                    JOIN knowledge_document_versions v ON v.document_id = d.id
                    WHERE d.id = %s AND d.parking_lot_id IS NOT DISTINCT FROM %s
                    ORDER BY v.version_no DESC
                    """,
                    (document_id, parking_lot_id),
                )
                versions = [
                    {"version_no": row[0], "status": row[1], "chunk_count": row[2],
                     "created_at": row[3].isoformat(),
                     "published_at": row[4].isoformat() if row[4] else ""}
                    for row in cursor.fetchall()
                ]
                version_filter = "AND v.version_no = %s" if version_no else "AND v.status <> 'ARCHIVED'"
                params = (document_id, parking_lot_id, version_no) if version_no else (document_id, parking_lot_id)
                cursor.execute(
                    f"""
                    SELECT v.id, v.version_no, v.status, v.chunk_count
                    FROM knowledge_documents d
                    JOIN knowledge_document_versions v ON v.document_id = d.id
                    WHERE d.id = %s AND d.parking_lot_id IS NOT DISTINCT FROM %s
                      {version_filter}
                    ORDER BY v.version_no DESC LIMIT 1
                    """,
                    params,
                )
                version = cursor.fetchone()
                if not version:
                    return {"version_no": 0, "status": "", "total": 0, "chunks": [], "versions": versions}
                cursor.execute(
                    """
                    SELECT ordinal, COALESCE(title, ''), content
                    FROM knowledge_chunks WHERE version_id = %s
                    ORDER BY ordinal LIMIT 100
                    """,
                    (version[0],),
                )
                return {
                    "version_no": int(version[1]),
                    "status": version[2],
                    "total": int(version[3]),
                    "chunks": [
                        {"ordinal": row[0], "section_title": row[1], "content": row[2]}
                        for row in cursor.fetchall()
                    ],
                    "versions": versions,
                }
        except Exception as exc:
            raise RagPipelineError("Không đọc được các đoạn tài liệu tri thức.") from exc
        finally:
            connection.close()

    def _list_documents_sync(self, parking_lot_id: Optional[str]) -> List[Dict[str, Any]]:
        connection = self._connect_sync()
        try:
            with connection.cursor() as cursor:
                # Cùng phạm vi với delete: bãi nào chỉ thấy tài liệu của bãi đó.
                scope_sql = "d.parking_lot_id = %s" if parking_lot_id else "d.parking_lot_id IS NULL"
                params: tuple[Any, ...] = (parking_lot_id,) if parking_lot_id else ()
                cursor.execute(
                    f"""
                    SELECT d.id::text, COALESCE(lv.file_name, d.file_name), d.category,
                           COALESCE(lv.uploaded_by, d.uploaded_by),
                           COALESCE(lv.chunk_count, d.chunk_count),
                           d.created_at, d.updated_at,
                           lv.version_no, lv.status, pv.version_no
                    FROM knowledge_documents d
                    LEFT JOIN LATERAL (
                        SELECT version_no, status, file_name, uploaded_by, chunk_count
                        FROM knowledge_document_versions v
                        WHERE v.document_id = d.id AND v.status <> 'ARCHIVED'
                        ORDER BY v.version_no DESC LIMIT 1
                    ) lv ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT version_no FROM knowledge_document_versions v
                        WHERE v.document_id = d.id AND v.status = 'PUBLISHED'
                    ) pv ON TRUE
                    WHERE {scope_sql}
                    ORDER BY d.updated_at DESC
                    """,
                    params,
                )
                return [
                    {
                        "document_id": row[0],
                        "file_name": row[1],
                        "category": row[2],
                        "uploaded_by": row[3],
                        "chunk_count": int(row[4] or 0),
                        "created_at": row[5].isoformat(),
                        "updated_at": row[6].isoformat(),
                        "latest_version_no": int(row[7] or 0),
                        "latest_status": row[8] or "",
                        "published_version_no": int(row[9] or 0),
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as exc:
            raise RagPipelineError("Không đọc được danh sách tài liệu tri thức.") from exc
        finally:
            connection.close()

    async def delete_document(
        self, document_id: str, parking_lot_id: Optional[str], draft_only: bool = False
    ) -> int:
        await self.ensure_schema()
        return await asyncio.to_thread(
            self._delete_document_sync, document_id, parking_lot_id, draft_only
        )

    def _delete_document_sync(
        self, document_id: str, parking_lot_id: Optional[str], draft_only: bool = False
    ) -> int:
        """`draft_only`: chỉ bỏ bản nháp, bản PUBLISHED (nếu có) vẫn phục vụ khách."""
        connection = self._connect_sync()
        try:
            with connection:
                with connection.cursor() as cursor:
                    scope_sql = (
                        "parking_lot_id = %s" if parking_lot_id else "parking_lot_id IS NULL"
                    )
                    scope_params: tuple[Any, ...] = (parking_lot_id,) if parking_lot_id else ()
                    cursor.execute(
                        f"SELECT 1 FROM knowledge_documents WHERE id = %s AND {scope_sql}",
                        (document_id, *scope_params),
                    )
                    if cursor.fetchone() is None:
                        return 0
                    if draft_only:
                        cursor.execute(
                            """
                            SELECT COUNT(*) FROM knowledge_chunks WHERE version_id IN (
                                SELECT id FROM knowledge_document_versions
                                WHERE document_id = %s AND status IN ('DRAFT', 'TESTED')
                            )
                            """,
                            (document_id,),
                        )
                        count = int(cursor.fetchone()[0])
                        cursor.execute(
                            """
                            DELETE FROM knowledge_document_versions
                            WHERE document_id = %s AND status IN ('DRAFT', 'TESTED')
                            """,
                            (document_id,),
                        )
                        # Tài liệu chỉ có mỗi bản nháp → gỡ luôn vỏ tài liệu.
                        cursor.execute(
                            """
                            DELETE FROM knowledge_documents d WHERE d.id = %s
                              AND NOT EXISTS (
                                  SELECT 1 FROM knowledge_document_versions v
                                  WHERE v.document_id = d.id AND v.status <> 'ARCHIVED'
                              )
                            """,
                            (document_id,),
                        )
                        return count
                    cursor.execute(
                        "SELECT COUNT(*) FROM knowledge_chunks WHERE document_id = %s",
                        (document_id,),
                    )
                    count = int(cursor.fetchone()[0])
                    cursor.execute("DELETE FROM knowledge_documents WHERE id = %s", (document_id,))
                    return count
        except Exception as exc:
            raise RagPipelineError("Không xoá được tài liệu khỏi pgvector.") from exc
        finally:
            connection.close()


pgvector_client = PgVectorClient()
