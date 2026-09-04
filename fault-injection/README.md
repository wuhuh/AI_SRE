# Fault Injection

The project supports the following fault classes. The in-service `/faults`
endpoints provide safe demo toggles. For Kubernetes, Chaos Mesh experiments can
replace these scripts.

| Case | Injection method |
| --- | --- |
| Redis connection pool exhausted | `python inject_fault.py redis_pool_exhausted --enable` |
| Redis slow command | `python inject_fault.py redis_slow_command --enable` |
| Thread pool exhausted | `python inject_fault.py thread_pool_exhausted --enable` |
| Slow SQL | `python inject_fault.py slow_sql --enable` |
| CPU saturation | `python inject_fault.py cpu_saturation --enable` |
| Memory pressure | `python inject_fault.py memory_pressure --enable` |
| Downstream HTTP timeout | `python inject_fault.py downstream_timeout --enable` |
| Database connection pool exhausted | Set `DB_POOL_SIZE=1` and generate load |
| Pod CrashLoopBackOff | Apply bad ConfigMap or readiness probe |
| RocketMQ message backlog | Stop consumers or send large volume |

Each fault case should produce Prometheus metrics, Loki logs, and traces.
After injection, use the Agent Runtime API to diagnose and verify recovery.