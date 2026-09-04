# Gateway 5xx

## Symptoms
- API gateway 5xx rate high
- downstream errors
- client impact

## Checks
1. `query_prometheus` gateway 5xx rate
2. `query_trace` error spans
3. `query_logs` status=500

## Recovery
- Route around unhealthy downstream
- Scale affected service
