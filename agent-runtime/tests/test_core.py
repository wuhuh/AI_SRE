from __future__ import annotations

import unittest

from app.agent.diagnostic import DiagnosticAgent
from app.agent.planner import Planner
from app.llm.mock import MockLLMProvider
from app.models import AgentState
from app.rag.retriever import Document, HybridRetriever
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry


class EchoTool(Tool):
    spec = ToolSpec(
        name="echo",
        description="echo arguments",
        parameters={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": [],
        },
        risk_level="READ_ONLY",
    )

    def execute(self, arguments, principal="agent"):
        return f"echo:{arguments.get('message', 'world')}"


class RequiredTool(Tool):
    spec = ToolSpec(
        name="required",
        description="requires message",
        parameters={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        risk_level="READ_ONLY",
    )

    def execute(self, arguments, principal="agent"):
        return arguments["message"]


class ToolRegistryTest(unittest.TestCase):
    def test_unknown_tool_returns_structured_error(self):
        registry = ToolRegistry()
        call = registry.call("missing", {})
        self.assertEqual(call.status, "ERROR")
        self.assertIn("Unknown tool", call.error)

    def test_validation_rejects_missing_required(self):
        registry = ToolRegistry()
        registry.register(RequiredTool())
        call = registry.call("required", {})
        self.assertEqual(call.status, "ERROR")
        self.assertIn("Missing required", call.error)

    def test_successful_tool_call(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "hello"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:hello")


class RetrieverTest(unittest.TestCase):
    def test_hybrid_retrieval_returns_expected_doc(self):
        docs = [
            Document(id="redis-pool", title="Redis connection pool exhausted",
                     content="maxclients reached; pool exhausted", tags=["redis", "payment"]),
            Document(id="slow-sql", title="Slow SQL",
                     content="database query high latency", tags=["database"]),
            Document(id="cpu", title="CPU saturation",
                     content="cpu usage 100%", tags=["cpu"]),
        ]
        retriever = HybridRetriever(docs, top_k=2)
        results = retriever.retrieve("Redis connection pool exhausted")
        self.assertEqual(results[0].id, "redis-pool")


class DiagnosticAgentTest(unittest.TestCase):
    def test_diagnosis_uses_tool_and_returns_structured_result(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=1, alert={"service": "payment-service", "alertName": "latency", "summary": "redis pool exhausted"})
        state.plan = ["echo"]
        result = agent.run(state)
        self.assertEqual(result.root_cause, "redis_connection_pool_exhausted")
        self.assertGreater(len(result.tool_calls), 0)
        self.assertEqual(result.tool_calls[0].name, "echo")


class PlannerTest(unittest.TestCase):
    def test_invalid_json_falls_back_to_default_plan(self):
        planner = Planner(MockLLMProvider(mode="invalid_json"))
        state = AgentState(incident_id=1, alert={})
        self.assertEqual(planner.plan(state), ["query_prometheus", "query_logs", "query_trace", "retrieve_runbook"])


if __name__ == "__main__":
    unittest.main()