"""Optional pgvector-backed document store.

This module is used when PostgreSQL + pgvector are available. It is optional
and falls back gracefully if `psycopg` / `pgvector` are not installed.
"""
from __future__ import annotations

import os
from typing import Any

try:
    import psycopg
    from pgvector.psycopg import register_vector
    PGVECTOR_AVAILABLE = True
except Exception:  # pragma: no cover
    PGVECTOR_AVAILABLE = False


class PGVectorDocumentStore:
    def __init__(self, dsn: str | None = None, table: str = "runbook_document"):
        self.dsn = dsn or os.getenv("DATABASE_URL", "postgresql://aisre:aisre@localhost:5432/aisre")
        self.table = table

    def ready(self) -> bool:
        return PGVECTOR_AVAILABLE

    def upsert(self, doc_id: str, title: str, content: str, embedding: list[float]) -> None:
        if not self.ready():
            raise RuntimeError("pgvector not available")
        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"INSERT INTO {self.table} (id, title, content, embedding) VALUES (%s, %s, %s, %s::vector) "
                    "ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content, embedding = EXCLUDED.embedding",
                    (doc_id, title, content, embedding),
                )

    def search(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if not self.ready():
            raise RuntimeError("pgvector not available")
        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, title, content, 1 - (embedding <=> %s::vector) AS similarity FROM {self.table} ORDER BY embedding <=> %s::vector LIMIT %s",
                    (embedding, embedding, top_k),
                )
                rows = cur.fetchall()
        return [{"id": r[0], "title": r[1], "content": r[2], "similarity": float(r[3])} for r in rows]