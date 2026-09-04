# Interview Preparation

## 50 Likely Questions

1. Why design Multi-Agent instead of one agent?  
   Because planner/diagnoser/verifier have separate responsibilities, state boundaries and evaluation targets.

2. Why not just one agent?  
   One agent is harder to test, observe and constrain permissions.

3. How does the Agent avoid infinite loops?  
   `MAX_STEPS` in `DiagnosticAgent` and timeout/retry wrappers.

4. What are the roles of Metrics, Logs, Trace?  
   Metrics give trends, logs give events, traces give request path.

5. How do you locate Root Cause?  
   Correlate metrics anomalies -> slow/error traces -> logs -> runbook evidence.

6. Why do you need Evidence?  
   To prove each LLM conclusion with observable data.

7. Why is RAG hybrid?  
   BM25 handles exact keywords, vectors handle semantic similarity, fusion improves recall.

8. Why use RocketMQ?  
   Decouple control plane from agent runtime, provide retry/backlog/at-least-once delivery.

9. Why use Redis?  
   Alert dedup TTL, rate limit, cache, distributed state.

10. What if a duplicate RocketMQ message arrives?  
    Persistent `idempotency_key` and duplicate detection on `agent_task`.

11. How is task idempotency guaranteed?  
    Unique `idempotencyKey` per task; repository lookup before processing.

12. What if Agent Runtime crashes?  
    Checkpointed `AgentState`/task rows allow resume or re-queue.

13. How do you keep tools safe?  
    Risk classification, RBAC, parameter validation, approval for HIGH_RISK, rate limit, audit.

14. Why Human-in-the-loop?  
    High-risk remediation must not be fully autonomous.

15. How prevent prompt injection?  
    Treat tool results as untrusted data, limit tool permissions, do not execute shell.

16. What if LLM times out?  
    Timeout wrapper, fallback to default plan, structured error.

17. How do you evaluate?  
    Evaluation cases and runner compute accuracy, latency, tool calls, tokens.

18. How do you inject faults?  
    `/faults` endpoints, env toggles, later Chaos Mesh.

19. How prove the project works?  
    Real metrics/logs/traces + E2E demo + reproducible benchmark.

20. Explain alert dedup algorithm.  
    Fingerprint = service + alertName + resource; Redis SETNX with TTL.

21. Why not use a single LLM prompt for diagnosis?  
    Tools/evidence need explicit state and permission boundaries.

22. How do you aggregate alerts into one incident?  
    Same service and overlapping active incident window.

23. What is your state machine?  
    DETECTED -> TRIAGING -> DIAGNOSING -> ROOT_CAUSE_FOUND -> WAITING_APPROVAL -> REMEDIATING -> VERIFYING -> RESOLVED/FAILED.

24. How does approval flow work?  
    High-risk tool call creates Approval PENDING; API decision updates status and triggers remediation.

25. What is Context Management?  
    Keep recent steps, evidence summary, tool result summary and budget instead of raw logs.

26. How do you handle long tool results?  
    Persist raw result, keep summary + reference in context.

27. What is a Tool Registry?  
    Central map of tools with specs, validation, rate limiter and permission.

28. How do you test LLM instability?  
    Mock provider modes: invalid_json, unknown_tool; plus tests for timeout/429.

29. How do you test tools?  
    Success, timeout, invalid argument, backend failure, unauthorized.

30. How do you measure Token Usage?  
    LLMResult carries input/output tokens; persisted in run report.

31. Why PostgreSQL?  
    Relational state, audit/history, pgvector for RAG.

32. Why OTel Collector?  
    Vendor-neutral ingestion and export of traces/metrics.

33. How do you correlate logs and traces?  
    Include traceId/spanId/requestId in logs.

34. What is Evidence Precision/Recall?  
    Compare predicted evidence against expected evidence in evaluation cases.

35. How do you handle unknown tool calls?  
    Registry returns structured ERROR; agent can continue/fallback.

36. How do you prevent alert storms?  
    Redis TTL dedup, aggregation, debounce.

37. How do you scale Agent Runtime?  
    Stateless consume from RocketMQ; tasks persisted in DB; can run multiple replicas.

38. What is the checkpoint store?  
    Persist AgentState after each step so crash can resume.

39. How does Verification decide recovered?  
    Re-check metrics/logs/traces; LLM returns RECOVERED/NOT_RECOVERED/UNKNOWN.

40. Why not auto-resolve if verification unknown?  
    Unknown means keep incident open or escalate.

41. What is in knowledge base?  
    Runbooks, postmortems, troubleshooting guides, architecture, service dependency.

42. How many runbooks?  
    20+ Markdown runbooks in `knowledge-base/runbooks`.

43. How to reproduce a demo?  
    `docker compose up -d`, inject fault, post alert, see agent diagnosis.

44. How to run evaluation offline?  
    Use MockLLMProvider and fake tools; no internet needed.

45. How to run integration tests?  
    Testcontainers for PostgreSQL/Redis/RocketMQ; contract tests between Java/Python APIs.

46. What is the API contract?  
    JSON schemas for alert, task, diagnosis, verification.

47. How to monitor control plane?  
    Actuator/OpenTelemetry endpoints (add micrometer dependency in production).

48. What is the CI pipeline?  
    Java build, Python lint/test, unit tests, docker build.

49. What are future improvements?  
    Real LLM provider, pgvector, front-end, Chaos Mesh, more evaluation cases.

50. How is this project different from a demo?  
    It has real state, real tool registry, evidence persistence, evaluation and deployment.