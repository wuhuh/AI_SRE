# Downstream HTTP Timeout

## Symptoms
- Upstream sees 504/503
- Downstream service slow
- Trace shows HTTP client span timeout

## Checks
1. `query_trace` error spans
2. `query_prometheus` downstream latency
3. `query_logs` timeout messages

## Recovery
- Increase timeout with retry budget
- Scale downstream or fix its bottleneck
