"""Idempotency store for at-least-once message consumption."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


class IdempotencyStore:
    def is_processed(self, key: str) -> bool:
        raise NotImplementedError

    def mark_processed(self, key: str) -> None:
        raise NotImplementedError


class FileIdempotencyStore(IdempotencyStore):
    def __init__(self, base_dir: str | os.PathLike[str] | None = None, ttl_seconds: int = 86400):
        self.base_dir = Path(base_dir or os.getenv("IDEMPOTENCY_DIR", "idempotency"))
        self.ttl_seconds = ttl_seconds
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return self.base_dir / f"{safe}.json"

    def is_processed(self, key: str) -> bool:
        path = self._path(key)
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return False
            return True
        except Exception:
            return False

    def mark_processed(self, key: str) -> None:
        self._path(key).write_text(
            json.dumps({"key": key, "ts": time.time()}),
            encoding="utf-8",
        )