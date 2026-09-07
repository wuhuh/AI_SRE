"""P2-FI-08: 平台自监控指标（monitoring the monitor）。"""
from prometheus_client import Counter, Gauge, Histogram

TOOL_CALLS_TOTAL = Counter(
    "aisre_tool_calls_total", "工具调用计数", ["tool", "status"]
)
DIAGNOSIS_DURATION = Histogram(
    "aisre_diagnosis_duration_seconds", "诊断耗时", buckets=(1, 5, 10, 15, 30, 60, 120)
)
DIAGNOSES_TOTAL = Counter(
    "aisre_diagnoses_total", "诊断完成计数", ["status"]
)
TASKS_PENDING = Gauge("aisre_tasks_pending", "待认领任务数")
