import shutil
import unittest
from pathlib import Path

from app.checkpoint import FileCheckpointStore
from app.models import AgentState, Evidence, ToolCall


class CrashRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).resolve().parent / ".tmp_crash"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_checkpoint_roundtrip_preserves_agent_state(self):
        store = FileCheckpointStore(self.tmp)
        state = AgentState(
            incident_id=7,
            alert={"service": "payment-service", "summary": "redis"},
            plan=["query_prometheus"],
            tool_results={"query_prometheus": "ok"},
            evidence=[Evidence(source="prometheus", key="k", content="v")],
            tool_calls=[ToolCall(name="query_prometheus", arguments={}, status="SUCCESS", result_summary="ok")],
            step=1,
            status="DIAGNOSED",
        )
        store.save(7, state)

        loaded = store.load(7)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.incident_id, 7)
        self.assertEqual(loaded.status, "DIAGNOSED")
        self.assertEqual(loaded.step, 1)
        self.assertEqual(loaded.tool_calls[0].name, "query_prometheus")
        self.assertEqual(loaded.evidence[0].source, "prometheus")


if __name__ == "__main__":
    unittest.main()