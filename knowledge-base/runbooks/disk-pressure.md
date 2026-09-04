# Disk Pressure

## Symptoms
- pod eviction due to disk pressure
- logs write failures
- node disk usage high

## Checks
1. `get_events` Evicted
2. `query_prometheus` container_fs_usage_bytes
3. `query_logs` "no space left"

## Recovery
- Clean logs / increase PV
- Move write-heavy pods to larger disk nodes
