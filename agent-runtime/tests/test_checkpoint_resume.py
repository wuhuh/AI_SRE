"""P0-09: 崩溃恢复 —— 每步存档 + 原子写 + 断点续跑 + 幂等返回。

模拟"进程被 kill -9"：诊断第二步抛出（此时第一步的 checkpoint 已落盘），
新 runner 从 checkpoint 续跑，剩余工具不重复执行；已完成的诊断直接返回不烧 LLM。
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.agent.runner import AgentRunner
from app.checkpoint import FileCheckpointStore
from app.llm.base import LLMProvider, LLMResult
from app.llm.mock import MockLLMProvider
from app.tools.registry import ToolRegistry


class CountingRegistry(ToolRegistry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed: list[str] = []

    def call(self, name, arguments, principal="agent"):
        self.executed.append(name)
        return super().call(name, arguments, principal=principal)


def _stub_registry() -> CountingRegistry:
    """注册 4 个只读 stub 工具，让 MockLLM 的计划真正执行（空 registry 会静默跳过）。"""
    from app.tools.base import Tool, ToolSpec

    registry = CountingRegistry()
    for name in ("query_prometheus", "query_logs", "query_trace", "retrieve_runbook"):
        class StubTool(Tool):
            spec = ToolSpec(name=name, description="stub",
                            parameters={"type": "object", "properties": {}}, risk_level="READ_ONLY")

            def execute(self, arguments, principal="agent"):
                return '{"status":"success"}'
        registry.register(StubTool())
    return registry


class CountingLLM(LLMProvider):
    """包一层调用计数（验证幂等返回不消耗 LLM）。"""

    def __init__(self, inner: LLMProvider):
        self.inner = inner
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        return self.inner.complete(messages, tools)


def _runner(llm, store, registry) -> AgentRunner:
    return AgentRunner(llm=llm, registry=registry, retriever=None, checkpoint_store=store)


class CrashResumeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = FileCheckpointStore(self.tmp.name)
        self.alert = {"service": "payment-service", "alertName": "HighLatency",
                      "severity": "P1", "summary": "payment latency high"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_crash_midway_resumes_without_replaying_tools(self):
        llm = CountingLLM(MockLLMProvider())
        registry = _stub_registry()
        runner = _runner(llm, self.store, registry)
        runner.diagnostic.on_step = lambda s: self.store.save(s.incident_id, s)

        # 模拟 kill -9：第一个工具执行完（已存档），第二个工具执行时进程死亡
        original = runner.diagnostic._execute_tool
        state = {"count": 0}

        def crashy_execute(state_arg, tool_name):
            if state["count"] >= 1:
                raise RuntimeError("simulated kill -9")
            state["count"] += 1
            return original(state_arg, tool_name)

        runner.diagnostic._execute_tool = crashy_execute
        with self.assertRaises(RuntimeError):
            runner.run_diagnosis(77, self.alert)

        # 第一步之后已有存档：step=1，pending 剩余 3 个工具
        saved = self.store.load(77)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.step, 1)
        self.assertEqual(len(saved.pending), 3)
        self.assertEqual(registry.executed, ["query_prometheus"])

        # 新进程（新 runner）从 checkpoint 续跑
        registry2 = _stub_registry()
        # 续跑必须带着已执行的 tool_results —— registry 只差在计数，状态在 state 里
        llm2 = CountingLLM(MockLLMProvider())
        runner2 = _runner(llm2, self.store, registry2)
        runner2.diagnostic.on_step = lambda s: self.store.save(s.incident_id, s)
        result = runner2.run_diagnosis(77, self.alert)

        self.assertTrue(result.resumed)
        self.assertIsNotNone(result.diagnosis)
        self.assertNotEqual("unknown", result.diagnosis.root_cause)
        # 已执行的 query_prometheus 未被重放
        self.assertNotIn("query_prometheus", registry2.executed)
        # 续跑执行剩余工具：logs/trace 走 registry（runbook 走内部路径，不经过 registry.call）
        self.assertEqual(registry2.executed, ["query_logs", "query_trace"])
        self.assertEqual(len(result.state.tool_calls), 4)

        # 幂等：已完成诊断直接返回，不再调用 LLM
        calls_before = llm2.calls
        again = runner2.run_diagnosis(77, self.alert)
        self.assertTrue(again.resumed)
        self.assertEqual(again.diagnosis.root_cause, result.diagnosis.root_cause)
        self.assertEqual(llm2.calls, calls_before)
        self.assertEqual(again.duration_ms, 0)

    def test_torn_tmp_file_is_replaced_atomically(self):
        # 崩溃留下的半截 .tmp：save 后被原子替换，load 始终拿到完整数据
        base = Path(self.tmp.name)
        (base / "88.json.tmp").write_text('{"incident_id": 88, "trunc', encoding="utf-8")
        llm = CountingLLM(MockLLMProvider())
        runner = _runner(llm, self.store, ToolRegistry())
        result = runner.run_diagnosis(88, self.alert)
        self.assertFalse(result.resumed)
        self.assertIsNotNone(self.store.load(88))
        self.assertFalse((base / "88.json.tmp").exists(), "原子替换后不应残留 tmp 文件")

    def test_corrupted_checkpoint_falls_back_to_fresh_run(self):
        (Path(self.tmp.name) / "99.json").write_text('{"incident_id": 99, "half', encoding="utf-8")
        runner = _runner(CountingLLM(MockLLMProvider()), self.store, ToolRegistry())
        result = runner.run_diagnosis(99, self.alert)
        self.assertFalse(result.resumed, "损坏 checkpoint 宁可重跑，不带病恢复")
        self.assertIsNotNone(result.diagnosis)


if __name__ == "__main__":
    unittest.main()
