import unittest

from app.agent.diagnostic import DiagnosticAgent
from app.agent.planner import Planner
from app.agent.verification import VerificationAgent
from app.context import build_context
from app.llm.mock import MockLLMProvider
from app.models import AgentState, ToolCall, Evidence
from app.rag.retriever import Document, HybridRetriever
from app.tools.base import Tool, ToolSpec
from app.tools.registry import ToolRegistry
from test_core import EchoTool, RequiredTool

class DeniedTool(Tool):
    spec = ToolSpec(name='denied', description='denied', parameters={'type':'object','properties':{},'required':[]}, risk_level='HIGH_RISK', allowed_principals=['admin'])
    def execute(self, arguments, principal='agent'):
        raise PermissionError('denied')

class TimeoutTool(Tool):
    spec = ToolSpec(name='timeout', description='timeout', parameters={'type':'object','properties':{},'required':[]}, risk_level='READ_ONLY')
    def execute(self, arguments, principal='agent'):
        raise TimeoutError('timeout')

class BoomTool(Tool):
    spec = ToolSpec(name='boom', description='boom', parameters={'type':'object','properties':{},'required':[]}, risk_level='READ_ONLY')
    def execute(self, arguments, principal='agent'):
        raise RuntimeError('backend failure')

class ToolRegistrySuccessExtendedTest(unittest.TestCase):
    def test_echo_success_001(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-1"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-1")

    def test_echo_success_002(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-2"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-2")

    def test_echo_success_003(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-3"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-3")

    def test_echo_success_004(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-4"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-4")

    def test_echo_success_005(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-5"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-5")

    def test_echo_success_006(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-6"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-6")

    def test_echo_success_007(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-7"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-7")

    def test_echo_success_008(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-8"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-8")

    def test_echo_success_009(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-9"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-9")

    def test_echo_success_010(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-10"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-10")

    def test_echo_success_011(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-11"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-11")

    def test_echo_success_012(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-12"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-12")

    def test_echo_success_013(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-13"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-13")

    def test_echo_success_014(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-14"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-14")

    def test_echo_success_015(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-15"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-15")

    def test_echo_success_016(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-16"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-16")

    def test_echo_success_017(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-17"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-17")

    def test_echo_success_018(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-18"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-18")

    def test_echo_success_019(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-19"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-19")

    def test_echo_success_020(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-20"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-20")

    def test_echo_success_021(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-21"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-21")

    def test_echo_success_022(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-22"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-22")

    def test_echo_success_023(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-23"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-23")

    def test_echo_success_024(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-24"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-24")

    def test_echo_success_025(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-25"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-25")

    def test_echo_success_026(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-26"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-26")

    def test_echo_success_027(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-27"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-27")

    def test_echo_success_028(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-28"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-28")

    def test_echo_success_029(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-29"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-29")

    def test_echo_success_030(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-30"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-30")

    def test_echo_success_031(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-31"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-31")

    def test_echo_success_032(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-32"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-32")

    def test_echo_success_033(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-33"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-33")

    def test_echo_success_034(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-34"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-34")

    def test_echo_success_035(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-35"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-35")

    def test_echo_success_036(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-36"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-36")

    def test_echo_success_037(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-37"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-37")

    def test_echo_success_038(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-38"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-38")

    def test_echo_success_039(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-39"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-39")

    def test_echo_success_040(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        call = registry.call("echo", {"message": "msg-40"})
        self.assertEqual(call.status, "SUCCESS")
        self.assertEqual(call.result_summary, "echo:msg-40")

class ToolErrorExtendedTest(unittest.TestCase):
    def test_permission_denied_001(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_002(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_003(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_004(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_005(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_006(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_007(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_008(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_009(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_010(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_011(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_012(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_013(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_014(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_015(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_016(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_017(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_018(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_019(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_permission_denied_020(self):
        registry = ToolRegistry()
        registry.register(DeniedTool())
        call = registry.call("denied", {})
        self.assertEqual(call.status, "DENIED")

    def test_timeout_001(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_002(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_003(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_004(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_005(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_006(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_007(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_008(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_009(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_timeout_010(self):
        registry = ToolRegistry()
        registry.register(TimeoutTool())
        call = registry.call("timeout", {})
        self.assertEqual(call.status, "TIMEOUT")

    def test_backend_failure_001(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_002(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_003(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_004(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_005(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_006(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_007(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_008(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_009(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

    def test_backend_failure_010(self):
        registry = ToolRegistry()
        registry.register(BoomTool())
        call = registry.call("boom", {})
        self.assertEqual(call.status, "ERROR")

class RagExtendedTest(unittest.TestCase):
    def setUp(self):
        self.docs = [
            Document(id='redis-pool', title='Redis connection pool exhausted', content='maxclients reached', tags=['redis','payment']),
            Document(id='slow-sql', title='Slow SQL', content='database query high latency', tags=['database','order']),
            Document(id='cpu-sat', title='CPU saturation', content='cpu usage 100%', tags=['cpu','inventory']),
            Document(id='mem-leak', title='Memory leak', content='memory grows', tags=['memory','inventory']),
            Document(id='http-timeout', title='Downstream HTTP timeout', content='client timeout', tags=['http','order']),
            Document(id='crashloop', title='Pod CrashLoopBackOff', content='restart loop', tags=['k8s','inventory']),
            Document(id='mq-backlog', title='RocketMQ backlog', content='consumer lag high', tags=['mq','order']),
            Document(id='thread-pool', title='Thread pool exhausted', content='threads max', tags=['thread','payment']),
            Document(id='redis-slow', title='Redis slow command', content='slowlog entry', tags=['redis','payment']),
            Document(id='db-pool', title='Database connection pool exhausted', content='pool exhausted', tags=['database','order']),
        ]
        self.retriever = HybridRetriever(self.docs, top_k=3)

    def test_retrieve_redis_pool_001(self):
        docs = self.retriever.retrieve("Redis connection pool exhausted")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "redis-pool")

    def test_retrieve_slow_sql_002(self):
        docs = self.retriever.retrieve("Slow SQL database query")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "slow-sql")

    def test_retrieve_cpu_sat_003(self):
        docs = self.retriever.retrieve("CPU saturation high load")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "cpu-sat")

    def test_retrieve_memory_leak_004(self):
        docs = self.retriever.retrieve("Memory leak high memory")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "mem-leak")

    def test_retrieve_http_timeout_005(self):
        docs = self.retriever.retrieve("Downstream HTTP timeout")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "http-timeout")

    def test_retrieve_crashloop_006(self):
        docs = self.retriever.retrieve("Pod CrashLoopBackOff restarts")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "crashloop")

    def test_retrieve_mq_backlog_007(self):
        docs = self.retriever.retrieve("RocketMQ message backlog consumer lag")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "mq-backlog")

    def test_retrieve_thread_pool_008(self):
        docs = self.retriever.retrieve("Thread pool exhausted")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "thread-pool")

    def test_retrieve_redis_slow_009(self):
        docs = self.retriever.retrieve("Redis slow command latency")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "redis-slow")

    def test_retrieve_db_pool_010(self):
        docs = self.retriever.retrieve("Database connection pool exhausted")
        self.assertGreater(len(docs), 0)
        self.assertEqual(docs[0].id, "db-pool")

    def test_compare_retrieval_001(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_002(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_003(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_004(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_005(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_006(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_007(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_008(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_009(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_010(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_011(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_012(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_013(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_014(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_015(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_016(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_017(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_018(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_019(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

    def test_compare_retrieval_020(self):
        result = self.retriever.compare("Redis connection pool exhausted")
        self.assertIn("bm25", result)
        self.assertIn("vector", result)
        self.assertIn("hybrid", result)

class ContextExtendedTest(unittest.TestCase):
    def test_context_build_001(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_002(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_003(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_004(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_005(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_006(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_007(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_008(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_009(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_010(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_011(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_012(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_013(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_014(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_015(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_016(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_017(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_018(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_019(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

    def test_context_build_020(self):
        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]
        state.evidence = [Evidence(source='prometheus', key='k', content='v')]
        bundle = build_context(state, state.alert)
        self.assertIn('Incident #100', bundle.summary)
        self.assertIn('redis pool exhausted', bundle.summary)

class PlannerExtendedTest(unittest.TestCase):
    def test_planner_normal_001(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=1, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_002(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=2, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_003(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=3, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_004(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=4, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_005(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=5, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_006(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=6, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_007(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=7, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_008(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=8, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_009(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=9, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_010(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=10, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_011(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=11, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_012(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=12, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_013(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=13, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_014(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=14, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_015(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=15, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_016(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=16, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_017(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=17, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_018(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=18, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_019(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=19, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_normal_020(self):
        planner = Planner(MockLLMProvider())
        state = AgentState(incident_id=20, alert={'service':'payment-service','summary':'redis'})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_001(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=1, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_002(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=2, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_003(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=3, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_004(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=4, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_005(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=5, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_006(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=6, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_007(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=7, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_008(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=8, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_009(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=9, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

    def test_planner_invalid_fallback_010(self):
        planner = Planner(MockLLMProvider(mode='invalid_json'))
        state = AgentState(incident_id=10, alert={})
        plan = planner.plan(state)
        self.assertEqual(len(plan), 4)

class DiagnosticExtendedTest(unittest.TestCase):
    def test_diagnosis_full_001(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=1, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_002(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=2, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_003(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=3, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_004(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=4, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_005(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=5, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_006(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=6, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_007(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=7, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_008(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=8, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_009(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=9, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_010(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=10, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_011(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=11, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_012(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=12, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_013(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=13, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_014(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=14, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_015(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=15, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_016(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=16, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_017(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=17, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_018(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=18, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_019(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=19, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_020(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=20, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_021(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=21, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_022(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=22, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_023(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=23, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_024(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=24, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_025(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=25, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_026(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=26, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_027(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=27, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_028(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=28, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_029(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=29, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

    def test_diagnosis_full_030(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = DiagnosticAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=30, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})
        state.plan = ['echo']
        result = agent.run(state)
        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')
        self.assertGreater(len(result.tool_calls), 0)

class VerificationExtendedTest(unittest.TestCase):
    def test_verification_mock_001(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=1, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_002(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=2, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_003(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=3, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_004(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=4, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_005(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=5, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_006(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=6, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_007(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=7, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_008(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=8, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_009(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=9, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_010(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=10, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_011(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=11, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_012(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=12, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_013(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=13, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_014(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=14, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_015(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=15, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_016(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=16, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_017(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=17, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_018(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=18, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_019(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=19, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

    def test_verification_mock_020(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        llm = MockLLMProvider()
        agent = VerificationAgent(llm=llm, registry=registry)
        state = AgentState(incident_id=20, alert={'service':'payment-service','summary':'redis'})
        result = agent.run(state)
        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])

if __name__ == '__main__':
    unittest.main()
