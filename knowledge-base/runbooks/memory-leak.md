# Memory Leak / High Memory

## Symptoms
- RSS grows over time
- OOMKilled events
- JVM heap / Python memory high

## Checks
1. `query_prometheus` process_resident_memory_bytes
2. `get_pod` restarts / OOMKilled
3. `get_events` OOM

## Recovery
- Restart pod to release memory temporarily
- Profile heap dump / tracemalloc
