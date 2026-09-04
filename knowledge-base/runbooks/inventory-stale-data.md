# Inventory Stale Data

## Symptoms
- inventory response outdated
- database replica lag
- cache not invalidated

## Checks
1. `db_active_connections`
2. `query_logs` cache invalidation
3. `query_trace` cache span

## Recovery
- Invalidate cache
- Fix CDC / replication lag
