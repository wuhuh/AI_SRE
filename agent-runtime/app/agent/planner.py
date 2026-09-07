from __future__ import annotations

# P2-AR-10: Planner 决策——删除 LLM 预规划（装饰调用，与逐步 LLM 决策重复），
# 保留固定初始计划；真规划待 LLM function calling 方案（AR-02 中期）时重建。
DEFAULT_PLAN = [
    "query_prometheus",
    "query_logs",
    "query_trace",
    "retrieve_runbook",
]
