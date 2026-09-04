# Slow SQL

## Symptoms
- DB query latency high
- High DB CPU
- Slow query log entries

## Checks
1. `db_slow_query`
2. `explain_query`
3. `query_trace` database span duration

## Recovery
- Add missing index
- Rewrite query
- Increase statement timeout as temporary mitigation
