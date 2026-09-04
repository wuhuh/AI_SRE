# Redis Connection Pool Exhausted

## Symptoms
- payment-service P99 latency high
- Redis active connections = maxclients
- logs contain "pool exhausted"

## Checks
1. `redis_info` -> connected_clients
2. `query_prometheus` -> redis connected clients
3. `query_logs` keyword "pool exhausted"

## Recovery
- Increase maxclients or connection pool size after confirming no connection leak
- Restart payment-service if a leak is suspected
