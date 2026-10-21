"""Checkpoint 隔离：同一 incident 的不同诊断轮次不能复用上一轮结果。

回归背景：checkpoint 原先只按 incident_id 存，重诊任务（同一个 incident、
新的 task id）会直接命中上一轮已完成的 DiagnosisResult，自动重诊环失效。
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.agent.runner import AgentRunner
from app.checkpoint import FileCheckpointStore
from app.llm.base import LLMProvider
from app.models import AgentState, LLMResult
from app.tools.registry import ToolRegistry


class SequenceLLM(LLMProvider):
    """第一次返回 slow_sql，第二次返回 cpu_saturation，便于区分不同轮次。"""

    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        root = "slow_sql" if self.calls == 1 else "cpu_saturation"
        return LLMResult(
            json.dumps({
                "rootCause": root,
                "confidence": 0.8,
                "evidence": [],
                "recommendedActions": [],
            }),
            input_tokens=10,
            output_tokens=5,
        )


ALERT = {"service": "payment-service", "summary": "latency high"}


class CheckpointScopeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = FileCheckpointStore(self.tmp.name)
        self.llm = SequenceLLM()
        self.runner = AgentRunner(
            llm=self.llm, registry=ToolRegistry(), retriever=None,
            checkpoint_store=self.store,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_round_key_does_not_reuse_completed_diagnosis(self):
        first = self.runner.run_diagnosis(1, ALERT, run_key="task-1")
        self.assertFalse(first.resumed)
        self.assertEqual(first.diagnosis.root_cause, "slow_sql")
        self.assertEqual(self.llm.calls, 1)

        second = self.runner.run_diagnosis(1, ALERT, run_key="task-2")
        self.assertFalse(second.resumed, "新一轮 task 必须重新诊断")
        self.assertEqual(second.diagnosis.root_cause, "cpu_saturation")
        self.assertEqual(self.llm.calls, 2)

        # 同一个 task 重试：幂等返回，不再烧 LLM
        replay = self.runner.run_diagnosis(1, ALERT, run_key="task-1")
        self.assertTrue(replay.resumed)
        self.assertEqual(replay.diagnosis.root_cause, "slow_sql")
        self.assertEqual(self.llm.calls, 2)

        self.assertTrue((Path(self.tmp.name) / "task-1.json").exists())
        self.assertTrue((Path(self.tmp.name) / "task-2.json").exists())

    def test_checkpoint_roundtrip_keeps_llm_messages(self):
        self.runner.run_diagnosis(2, ALERT, run_key="task-9")
        loaded = self.store.load("task-9")
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.llm_messages)
        self.assertEqual(loaded.llm_messages[0]["role"], "system")

    def test_windows_unsafe_key_is_sanitized(self):
        state = AgentState(incident_id=3, alert=ALERT, status="DIAGNOSED")
        self.store.save("incident:3:task:7", state)
        self.assertTrue((Path(self.tmp.name) / "incident_3_task_7.json").exists())
        self.assertEqual(self.store.load("incident:3:task:7").incident_id, 3)


if __name__ == "__main__":
    unittest.main()
