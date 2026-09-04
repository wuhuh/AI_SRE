# Redis Slow Command / Latency

## Symptoms
- Redis latency high
- slowlog entries
- payment trace redis span high

## Checks
1. `redis_slowlog`
2. `redis_info` latency
3. `query_trace` redis span

## Recovery
- Optimize keys / use pipeline
- Remove hot keys
- Scale Redis or use cache-aside
