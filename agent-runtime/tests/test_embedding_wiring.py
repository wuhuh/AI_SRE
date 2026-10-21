"""RAG embedding 接线：真实 provider 可选启用 + 默认向量跨进程稳定。

背景：默认 embedding 原先用内置 hash()，受 PYTHONHASHSEED 影响；
一旦把向量落 pgvector，重启后查询向量与入库向量不在同一空间。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from app.main import _build_embedding_provider
from app.rag.embeddings import OpenAICompatibleEmbeddingProvider
from app.rag.retriever import Document, HybridRetriever, default_embedding

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DefaultEmbeddingStabilityTest(unittest.TestCase):
    def test_vector_is_stable_across_hash_seeds(self):
        code = (
            "import json;"
            "from app.rag.retriever import default_embedding;"
            "print(json.dumps(default_embedding('redis pool exhausted')))"
        )
        outputs = []
        for seed in ("1", "2"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            outputs.append(subprocess.check_output(
                [sys.executable, "-c", code], cwd=PROJECT_ROOT, env=env, text=True).strip())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(json.loads(outputs[0]), default_embedding("redis pool exhausted"))

    def test_different_text_gets_different_vector(self):
        self.assertNotEqual(default_embedding("redis pool"), default_embedding("slow sql"))


class EmbeddingProviderTest(unittest.TestCase):
    def test_hybrid_retriever_uses_injected_provider(self):
        class FakeProvider:
            def __init__(self):
                self.calls: list[str] = []

            def embed(self, text: str):
                self.calls.append(text)
                lower = text.lower()
                return [1.0 if "redis" in lower else 0.0,
                        1.0 if "sql" in lower else 0.0]

        provider = FakeProvider()
        docs = [
            Document(id="redis-pool", title="Redis pool", content="redis maxclients"),
            Document(id="slow-sql", title="Slow SQL", content="sql latency"),
        ]
        retriever = HybridRetriever(docs, embedding_provider=provider, top_k=1)
        self.assertEqual(len(provider.calls), 2, "初始化时必须嵌入全部文档")

        result = retriever.retrieve("redis pool")
        self.assertEqual(result[0].id, "redis-pool")
        self.assertEqual(provider.calls[-1], "redis pool")

    def test_factory_respects_env_switch(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "openai"}, clear=False):
            self.assertIsInstance(_build_embedding_provider(), OpenAICompatibleEmbeddingProvider)
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": ""}, clear=False):
            self.assertIsNone(_build_embedding_provider())

    def test_openai_embedding_provider_payload(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"embedding": [0.1, 0.2]}]}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

        with patch("httpx.post", fake_post):
            vector = OpenAICompatibleEmbeddingProvider(
                base_url="http://embed", api_key="test-key", model="embed-model",
            ).embed("hello")

        self.assertEqual(vector, [0.1, 0.2])
        self.assertEqual(captured["url"], "http://embed/embeddings")
        self.assertEqual(captured["json"]["input"], "hello")
        self.assertEqual(captured["json"]["model"], "embed-model")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-key")


if __name__ == "__main__":
    unittest.main()
