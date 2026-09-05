"""Hybrid RAG retriever: query rewrite -> BM25 + embedding -> fusion -> rerank.

No external vector database is required for the first version. The embedding
function is pluggable; the default implementation is a lightweight hashed
bag-of-ngrams useful for local demos and tests. In production, replace it with
pgvector or an embedding API.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

TOKEN_RE = re.compile(r"[a-z0-9_]+")


@dataclass
class Document:
    id: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)

    def text(self) -> str:
        return f"{self.title} {self.tags} {self.content}"


def default_tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def default_embedding(text: str, dimensions: int = 256) -> list[float]:
    vec = [0.0] * dimensions
    tokens = default_tokenize(text)
    for i, token in enumerate(tokens):
        idx = abs(hash(f"{token}:{i % 7}")) % dimensions
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class BM25:
    def __init__(self, docs: list[Document], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.avgdl = sum(len(default_tokenize(d.text())) for d in docs) / max(len(docs), 1)
        self.doc_freq: Counter[str] = Counter()
        self.doc_len: list[int] = []
        self.doc_tokens: list[Counter] = []
        for doc in docs:
            tokens = default_tokenize(doc.text())
            self.doc_len.append(len(tokens))
            counter = Counter(tokens)
            self.doc_tokens.append(counter)
            self.doc_freq.update(counter.keys())

    def score_all(self, query: str) -> list[float]:
        q_tokens = set(default_tokenize(query))
        n_docs = len(self.docs)
        scores = []
        for i, counter in enumerate(self.doc_tokens):
            score = 0.0
            dl = self.doc_len[i]
            for term in q_tokens:
                tf = counter.get(term, 0)
                if tf == 0:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += idf * (tf * (self.k1 + 1)) / denom
            scores.append(score)
        return scores


class HybridRetriever:
    def __init__(
        self,
        docs: list[Document],
        embedding_fn: Callable[[str], list[float]] | None = None,
        embedding_provider=None,
        top_k: int = 5,
    ):
        self.docs = docs
        self.embedding_fn = embedding_fn or getattr(embedding_provider, "embed", None) or default_embedding
        self.top_k = top_k
        self.bm25 = BM25(docs)
        self.doc_embeddings = [self.embedding_fn(d.text()) for d in docs]

    def retrieve(self, query: str, top_k: int | None = None) -> list[Document]:
        k = top_k or self.top_k
        rewritten = self._rewrite(query)
        bm25_scores = self.bm25.score_all(rewritten)
        vec_scores = self._cosine_scores(self._embed(rewritten))
        hybrid = [
            (i, 0.5 * bm25_scores[i] + 0.5 * vec_scores[i])
            for i in range(len(self.docs))
        ]
        hybrid.sort(key=lambda x: x[1], reverse=True)
        reranked = self._rerank(rewritten, hybrid[: k * 2])
        return [self.docs[i] for i, _ in reranked[:k]]

    def compare(self, query: str, top_k: int = 5) -> dict[str, list[str]]:
        """Return IDs for vector-only, BM25-only and hybrid retrieval."""
        bm25_scores = self.bm25.score_all(query)
        vec_scores = self._cosine_scores(self._embed(query))
        bm25_ids = [self.docs[i].id for i in sorted(range(len(self.docs)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]]
        vec_ids = [self.docs[i].id for i in sorted(range(len(self.docs)), key=lambda i: vec_scores[i], reverse=True)[:top_k]]
        hybrid = self.retrieve(query, top_k=top_k)
        return {"bm25": bm25_ids, "vector": vec_ids, "hybrid": [d.id for d in hybrid]}

    def _rewrite(self, query: str) -> str:
        q = query.lower().strip()
        replacements = {
            "connection pool": "redis pool exhausted",
            "caching dependency": "redis connection pool",
            "cache": "redis",
            "5xx": "error rate high",
            "p99": "latency slow",
        }
        for k, v in replacements.items():
            if k in q:
                q += " " + v
        return q

    def _embed(self, text: str) -> list[float]:
        return self.embedding_fn(text)

    def _cosine_scores(self, vec: list[float]) -> list[float]:
        return [
            sum(a * b for a, b in zip(vec, doc_vec))
            for doc_vec in self.doc_embeddings
        ]

    def _rerank(self, query: str, candidates: list[tuple[int, float]]) -> list[tuple[int, float]]:
        # Lightweight rerank: boost exact title/tag matches.
        q_terms = set(default_tokenize(query))
        reranked = []
        for idx, score in candidates:
            doc = self.docs[idx]
            doc_terms = set(default_tokenize(doc.title + " " + " ".join(doc.tags)))
            overlap = len(q_terms & doc_terms)
            reranked.append((idx, score + overlap * 0.1))
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked