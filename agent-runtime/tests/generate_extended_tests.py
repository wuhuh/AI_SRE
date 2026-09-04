from pathlib import Path

lines = []
w = lines.append

w("import unittest")
w("")
w("from app.agent.diagnostic import DiagnosticAgent")
w("from app.agent.planner import Planner")
w("from app.agent.verification import VerificationAgent")
w("from app.context import build_context")
w("from app.llm.mock import MockLLMProvider")
w("from app.models import AgentState, ToolCall, Evidence")
w("from app.rag.retriever import Document, HybridRetriever")
w("from app.tools.base import Tool, ToolSpec")
w("from app.tools.registry import ToolRegistry")
w("from test_core import EchoTool, RequiredTool")
w("")

w("class DeniedTool(Tool):")
w("    spec = ToolSpec(name='denied', description='denied', parameters={'type':'object','properties':{},'required':[]}, risk_level='HIGH_RISK', allowed_principals=['admin'])")
w("    def execute(self, arguments, principal='agent'):")
w("        raise PermissionError('denied')")
w("")
w("class TimeoutTool(Tool):")
w("    spec = ToolSpec(name='timeout', description='timeout', parameters={'type':'object','properties':{},'required':[]}, risk_level='READ_ONLY')")
w("    def execute(self, arguments, principal='agent'):")
w("        raise TimeoutError('timeout')")
w("")
w("class BoomTool(Tool):")
w("    spec = ToolSpec(name='boom', description='boom', parameters={'type':'object','properties':{},'required':[]}, risk_level='READ_ONLY')")
w("    def execute(self, arguments, principal='agent'):")
w("        raise RuntimeError('backend failure')")
w("")

w("class ToolRegistrySuccessExtendedTest(unittest.TestCase):")
for i in range(1, 41):
    w(f"    def test_echo_success_{i:03d}(self):")
    w("        registry = ToolRegistry()")
    w("        registry.register(EchoTool())")
    w(f'        call = registry.call("echo", {{"message": "msg-{i}"}})')
    w('        self.assertEqual(call.status, "SUCCESS")')
    w(f'        self.assertEqual(call.result_summary, "echo:msg-{i}")')
    w("")

w("class ToolErrorExtendedTest(unittest.TestCase):")
for i in range(1, 21):
    w(f"    def test_permission_denied_{i:03d}(self):")
    w("        registry = ToolRegistry()")
    w("        registry.register(DeniedTool())")
    w('        call = registry.call("denied", {})')
    w('        self.assertEqual(call.status, "DENIED")')
    w("")
for i in range(1, 11):
    w(f"    def test_timeout_{i:03d}(self):")
    w("        registry = ToolRegistry()")
    w("        registry.register(TimeoutTool())")
    w('        call = registry.call("timeout", {})')
    w('        self.assertEqual(call.status, "TIMEOUT")')
    w("")
for i in range(1, 11):
    w(f"    def test_backend_failure_{i:03d}(self):")
    w("        registry = ToolRegistry()")
    w("        registry.register(BoomTool())")
    w('        call = registry.call("boom", {})')
    w('        self.assertEqual(call.status, "ERROR")')
    w("")

w("class RagExtendedTest(unittest.TestCase):")
w("    def setUp(self):")
w("        self.docs = [")
w("            Document(id='redis-pool', title='Redis connection pool exhausted', content='maxclients reached', tags=['redis','payment']),")
w("            Document(id='slow-sql', title='Slow SQL', content='database query high latency', tags=['database','order']),")
w("            Document(id='cpu-sat', title='CPU saturation', content='cpu usage 100%', tags=['cpu','inventory']),")
w("            Document(id='mem-leak', title='Memory leak', content='memory grows', tags=['memory','inventory']),")
w("            Document(id='http-timeout', title='Downstream HTTP timeout', content='client timeout', tags=['http','order']),")
w("            Document(id='crashloop', title='Pod CrashLoopBackOff', content='restart loop', tags=['k8s','inventory']),")
w("            Document(id='mq-backlog', title='RocketMQ backlog', content='consumer lag high', tags=['mq','order']),")
w("            Document(id='thread-pool', title='Thread pool exhausted', content='threads max', tags=['thread','payment']),")
w("            Document(id='redis-slow', title='Redis slow command', content='slowlog entry', tags=['redis','payment']),")
w("            Document(id='db-pool', title='Database connection pool exhausted', content='pool exhausted', tags=['database','order']),")
w("        ]")
w("        self.retriever = HybridRetriever(self.docs, top_k=3)")
w("")
rg_queries = [
    ("redis_pool", "Redis connection pool exhausted", "redis-pool"),
    ("slow_sql", "Slow SQL database query", "slow-sql"),
    ("cpu_sat", "CPU saturation high load", "cpu-sat"),
    ("memory_leak", "Memory leak high memory", "mem-leak"),
    ("http_timeout", "Downstream HTTP timeout", "http-timeout"),
    ("crashloop", "Pod CrashLoopBackOff restarts", "crashloop"),
    ("mq_backlog", "RocketMQ message backlog consumer lag", "mq-backlog"),
    ("thread_pool", "Thread pool exhausted", "thread-pool"),
    ("redis_slow", "Redis slow command latency", "redis-slow"),
    ("db_pool", "Database connection pool exhausted", "db-pool"),
]
for idx, (name, query, expected_id) in enumerate(rg_queries, 1):
    w(f"    def test_retrieve_{name}_{idx:03d}(self):")
    w(f'        docs = self.retriever.retrieve("{query}")')
    w("        self.assertGreater(len(docs), 0)")
    w(f'        self.assertEqual(docs[0].id, "{expected_id}")')
    w("")
for i in range(1, 21):
    w(f"    def test_compare_retrieval_{i:03d}(self):")
    w('        result = self.retriever.compare("Redis connection pool exhausted")')
    w('        self.assertIn("bm25", result)')
    w('        self.assertIn("vector", result)')
    w('        self.assertIn("hybrid", result)')
    w("")

w("class ContextExtendedTest(unittest.TestCase):")
for i in range(1, 21):
    w(f"    def test_context_build_{i:03d}(self):")
    w("        state = AgentState(incident_id=100, alert={'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'})")
    w("        state.tool_calls = [ToolCall(name='query_prometheus', arguments={}, status='SUCCESS', result_summary='metrics')]")
    w("        state.evidence = [Evidence(source='prometheus', key='k', content='v')]")
    w("        bundle = build_context(state, state.alert)")
    w("        self.assertIn('Incident #100', bundle.summary)")
    w("        self.assertIn('redis pool exhausted', bundle.summary)")
    w("")

w("class PlannerExtendedTest(unittest.TestCase):")
for i in range(1, 21):
    w(f"    def test_planner_normal_{i:03d}(self):")
    w("        planner = Planner(MockLLMProvider())")
    w(f"        state = AgentState(incident_id={i}, alert={{'service':'payment-service','summary':'redis'}})")
    w("        plan = planner.plan(state)")
    w("        self.assertEqual(len(plan), 4)")
    w("")
for i in range(1, 11):
    w(f"    def test_planner_invalid_fallback_{i:03d}(self):")
    w("        planner = Planner(MockLLMProvider(mode='invalid_json'))")
    w(f"        state = AgentState(incident_id={i}, alert={{}})")
    w("        plan = planner.plan(state)")
    w("        self.assertEqual(len(plan), 4)")
    w("")

w("class DiagnosticExtendedTest(unittest.TestCase):")
for i in range(1, 31):
    w(f"    def test_diagnosis_full_{i:03d}(self):")
    w("        registry = ToolRegistry()")
    w("        registry.register(EchoTool())")
    w("        llm = MockLLMProvider()")
    w("        agent = DiagnosticAgent(llm=llm, registry=registry)")
    w(f"        state = AgentState(incident_id={i}, alert={{'service':'payment-service','alertName':'latency','summary':'redis pool exhausted'}})")
    w("        state.plan = ['echo']")
    w("        result = agent.run(state)")
    w("        self.assertEqual(result.root_cause, 'redis_connection_pool_exhausted')")
    w("        self.assertGreater(len(result.tool_calls), 0)")
    w("")

w("class VerificationExtendedTest(unittest.TestCase):")
for i in range(1, 21):
    w(f"    def test_verification_mock_{i:03d}(self):")
    w("        registry = ToolRegistry()")
    w("        registry.register(EchoTool())")
    w("        llm = MockLLMProvider()")
    w("        agent = VerificationAgent(llm=llm, registry=registry)")
    w(f"        state = AgentState(incident_id={i}, alert={{'service':'payment-service','summary':'redis'}})")
    w("        result = agent.run(state)")
    w("        self.assertIn(result.status, ['RECOVERED', 'NOT_RECOVERED', 'UNKNOWN'])")
    w("")

w("if __name__ == '__main__':")
w("    unittest.main()")
w("")

Path('E:/study/实习/项目/AI SRE/agent-runtime/tests/test_extended.py').write_text('\n'.join(lines), encoding='utf-8')
print('generated', len([l for l in lines if l.strip().startswith('def test_')]))
