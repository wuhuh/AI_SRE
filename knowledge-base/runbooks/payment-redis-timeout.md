# Payment Redis Timeout

## Symptoms
- payment calls redis timeout
- redis CPU high
- payment 5xx

## Checks
1. `redis_info`
2. `query_prometheus` redis commands duration
3. `query_logs` timeout

## Recovery
- Tune redis timeout
- Offload non-critical redis operations
