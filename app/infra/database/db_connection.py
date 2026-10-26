"""Quản lý kết nối PostgreSQL an toàn, tự động nhận diện và fallback đa môi trường (Host/Docker)."""
from __future__ import annotations

import os
import urllib.parse
from typing import Any, List, Optional, Tuple

import psycopg2
from app.util.logger import logger

def _redact_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.password:
            user = parsed.username or ""
            host = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            netloc = f"{user}:***@{host}{port}"
            return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        pass
    return url


# Cache URL đã kết nối thành công để không phải thử lại nhiều lần
_RESOLVED_URL_CACHE: dict[str, str] = {}


def resolve_db_candidates(db_url: str) -> List[str]:
    """Sinh danh sách các URL tiềm năng để thử kết nối, bao phủ mọi trường hợp của các dev:
    1. URL gốc được cấu hình.
    2. Nếu URL trỏ vào hostname container Docker (ai-db, database-vector, postgres, etc.) trên port 5432:
       Thử các cổng ánh xạ máy host: 5435 (mặc định của IPLMS), AI_DB_HOST_PORT, và 5432.
    3. Nếu URL trỏ vào 127.0.0.1 / localhost trên port 5432 nhưng Postgres chạy ở 5435:
       Thử port 5435.
    4. Nếu URL trỏ vào 127.0.0.1 / localhost trên port 5435 nhưng Postgres chạy native ở 5432:
       Thử port 5432.
    5. Hỗ trợ host.docker.internal nếu dev chạy từ trong container ra máy host.
    """
    if not db_url:
        return []

    candidates: List[str] = [db_url]

    try:
        parsed = urllib.parse.urlsplit(db_url)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port or 5432

        # Danh sách host thay thế khi đang ở host machine hoặc trong container
        docker_hosts = {"ai-db", "database-vector", "postgres", "ai_db", "db"}
        in_docker = os.path.exists("/.dockerenv")
        local_hosts = ["127.0.0.1", "localhost"] + (["host.docker.internal"] if in_docker else [])

        host_port_env = os.environ.get("AI_DB_HOST_PORT", "5435")
        try:
            custom_port = int(host_port_env)
        except ValueError:
            custom_port = 5435

        target_ports: List[int] = [custom_port, 5435, 5432]
        seen_ports: List[int] = []
        for p in target_ports:
            if p not in seen_ports:
                seen_ports.append(p)

        def make_url(new_host: str, new_port: int) -> str:
            netloc = f"{parsed.username or ''}"
            if parsed.password:
                netloc += f":{parsed.password}"
            if netloc:
                netloc += "@"
            netloc += f"{new_host}:{new_port}"
            return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

        # Nếu hostname là tên container trong docker-compose
        if hostname in docker_hosts:
            if not in_docker:
                candidates = []
            for lh in local_hosts:
                for p in seen_ports:
                    cand = make_url(lh, p)
                    if cand not in candidates:
                        candidates.append(cand)
            if db_url not in candidates:
                candidates.append(db_url)

        # Nếu hostname là localhost / 127.0.0.1
        elif hostname in ("127.0.0.1", "localhost"):
            for p in seen_ports:
                if p != port:
                    cand = make_url(hostname, p)
                    if cand not in candidates:
                        candidates.append(cand)
            if in_docker:
                for p in seen_ports:
                    cand = make_url("host.docker.internal", p)
                    if cand not in candidates:
                        candidates.append(cand)

    except Exception as exc:
        logger.warning(f"Lỗi phân tích URL DB ({exc}), chỉ dùng URL gốc.")

    return candidates


def _may_create_database(cand_url: str, db_url: str) -> bool:
    """Chỉ tự tạo DB trên URL đã cấu hình hoặc cổng map của chính DB AI (AI_DB_HOST_PORT).

    Ứng viên fallback khác (vd 5432 trên máy dev) có thể là Postgres của dự án khác (bug-029).
    """
    if cand_url == db_url:
        return True
    try:
        own_port = int(os.environ.get("AI_DB_HOST_PORT", "5435"))
        return urllib.parse.urlsplit(cand_url).port == own_port
    except ValueError:
        return False


def _ensure_database_exists(cand_url: str, connect_timeout: int = 3) -> bool:
    """Tự động khởi tạo database nếu server PostgreSQL đang chạy nhưng chưa có database đích."""
    try:
        from psycopg2 import sql

        parsed = urllib.parse.urlsplit(cand_url)
        dbname = (parsed.path or "").lstrip("/")
        if not dbname or dbname == "postgres":
            return False
        admin_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/postgres", "", ""))
        admin_conn = psycopg2.connect(admin_url, connect_timeout=connect_timeout)
        try:
            admin_conn.autocommit = True
            with admin_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if not cur.fetchone():
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
                    logger.info("Đã tự động tạo database %s trên %s:%s", dbname, parsed.hostname, parsed.port)
            return True
        finally:
            admin_conn.close()
    except Exception as exc:
        logger.warning("Không thể tự tạo database từ %s: %s", _redact_url(cand_url), exc)
        return False


def _try_register_vector(conn: Any) -> None:
    try:
        from pgvector.psycopg2 import register_vector as reg_vec

        reg_vec(conn)
    except Exception:
        # Môi trường PostgreSQL thuần trên Windows không cài extension pgvector C binary:
        # PgVectorClient chỉ chuyển sang chế độ mảng DOUBLE PRECISION[] khi bật
        # AI_EMBEDDING_ALLOW_NO_PGVECTOR (ai ADR-0001), không thì báo lỗi.
        conn.rollback()


def connect_with_fallback(
    db_url: str,
    connect_timeout: int = 3,
    register_vector: bool = False,
) -> Tuple[Any, str]:
    """Kết nối PostgreSQL với cơ chế tự động thử các ứng viên fallback đa môi trường.

    Returns:
        (connection, working_db_url)
    """
    if not db_url:
        raise ValueError("URL kết nối cơ sở dữ liệu rỗng.")

    # 1. Thử URL đã được resolve trong cache
    if db_url in _RESOLVED_URL_CACHE:
        cached_url = _RESOLVED_URL_CACHE[db_url]
        try:
            conn = psycopg2.connect(cached_url, connect_timeout=connect_timeout)
            if register_vector:
                _try_register_vector(conn)
            return conn, cached_url
        except Exception:
            _RESOLVED_URL_CACHE.pop(db_url, None)

    # 2. Thử lần lượt các candidates
    candidates = resolve_db_candidates(db_url)
    last_exc = None

    for cand_url in candidates:
        try:
            try:
                conn = psycopg2.connect(cand_url, connect_timeout=connect_timeout)
            except psycopg2.OperationalError as op_exc:
                if (
                    _may_create_database(cand_url, db_url)
                    and "does not exist" in str(op_exc)
                    and _ensure_database_exists(cand_url, connect_timeout)
                ):
                    conn = psycopg2.connect(cand_url, connect_timeout=connect_timeout)
                else:
                    raise
            if register_vector:
                _try_register_vector(conn)

            # Lưu vào cache để các lần gọi sau không mất thời gian thử lại
            _RESOLVED_URL_CACHE[db_url] = cand_url
            if cand_url != db_url:
                logger.warning(
                    "Database Fallback: dùng %s thay cho URL cấu hình %s",
                    _redact_url(cand_url),
                    _redact_url(db_url),
                )
            return conn, cand_url
        except Exception as exc:
            last_exc = exc
            continue

    if last_exc:
        raise last_exc
    raise psycopg2.OperationalError(
        f"Không thể kết nối tới bất kỳ ứng viên nào của DB: {[_redact_url(c) for c in candidates]}"
    )
