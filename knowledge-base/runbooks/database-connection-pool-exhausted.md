# Database Connection Pool Exhausted

## Symptoms
- Order-service latency high
- DB active connections max
- logs "HikariPool-1 - Connection is not available"

## Checks
1. `db_active_connections`
2. `query_logs` keyword "HikariPool"
3. `query_trace` slow DB spans

## Recovery
- Reduce connection pool per pod or scale readers
- Identify slow SQL holding connections
