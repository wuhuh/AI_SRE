# CPU Saturation

## Symptoms
- Container CPU > 90%
- QPS drops or latency increases
- Load average high

## Checks
1. `query_prometheus` container_cpu_usage_seconds_total
2. `list_pods` to identify noisy neighbour
3. `get_pod` resources

## Recovery
- Scale deployment horizontally
- Investigate hot code path or infinite loop
