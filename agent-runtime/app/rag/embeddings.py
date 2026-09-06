"""Embedding provider abstraction.

Tests use DeterministicMockEmbedding. Production can configure an
OpenAI-compatible embedding endpoint.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicMockEmbedding(EmbeddingProvider):
    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for i, ch in enumerate(text):
            vec[(ord(ch) + i * 7) % self.dimensions] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 model: str = "text-embedding-3-small"):
        self.base_url = (base_url or os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY", "")
        self.model = model

    def embed(self, text: str) -> list[float]:
        import httpx
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            json={"model": self.model, "input": text},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
