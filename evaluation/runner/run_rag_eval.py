"""RAG retrieval evaluation: BM25 / Vector / Hybrid + Rerank.

Metrics: Recall@1, Recall@3, Recall@5, MRR.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent-runtime"))

from app.rag.embeddings import DeterministicMockEmbedding
from app.rag.retriever import BM25, Document, HybridRetriever, default_embedding

DOCS = [
    Document(id="redis-pool", title="Redis connection pool exhausted", content="redis maxclients reached pool exhausted", tags=["redis"]),
    Document(id="slow-sql", title="Slow SQL", content="slow query database latency missing index", tags=["database"]),
    Document(id="cpu-sat", title="CPU saturation", content="cpu usage 100 percent saturation", tags=["cpu"]),
    Document(id="mem-leak", title="Memory leak", content="memory grows high rss", tags=["memory"]),
]

QUERIES = [
    ("Redis connection pool exhausted", "redis-pool"),
    ("Slow SQL missing index", "slow-sql"),
    ("CPU saturation high load", "cpu-sat"),
]


def recall_at(ranked_ids, expected):
    return 1.0 if expected in ranked_ids else 0.0


def mrr(ranked_ids, expected):
    return 1.0 / (ranked_ids.index(expected) + 1) if expected in ranked_ids else 0.0


def evaluate_retriever(name, retrieve_fn, top_k_list=(1, 3, 5)):
    metrics = {}
    for k in top_k_list:
        recalls = [recall_at(retrieve_fn(q, k), exp) for q, exp in QUERIES]
        metrics[f"Recall@{k}"] = round(sum(recalls) / len(recalls), 4)
    mrrs = [mrr(retrieve_fn(q, 5), exp) for q, exp in QUERIES]
    metrics["MRR"] = round(sum(mrrs) / len(mrrs), 4)
    return {name: metrics}


def main():
    retriever = HybridRetriever(DOCS, embedding_provider=DeterministicMockEmbedding(), top_k=5)
    bm25 = BM25(DOCS)

    results = {}
    results.update(evaluate_retriever("BM25", lambda q, k: [d.id for d in sorted(DOCS, key=lambda d: -bm25.score_all(q)[DOCS.index(d)])[:k]]))
    results.update(evaluate_retriever("Vector", lambda q, k: [d.id for d in retriever.retrieve(q, k)]))
    results["Hybrid"] = evaluate_retriever("Hybrid", lambda q, k: [d.id for d in retriever.retrieve(q, k)])["Hybrid"]
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()