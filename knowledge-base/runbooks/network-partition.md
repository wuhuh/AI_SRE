# Network Partition

## Symptoms
- intermittent connection timeouts between services
- leader election flapping
- trace gaps

## Checks
1. `query_trace` missing downstream spans
2. `query_logs` connection reset
3. k8s network policies

## Recovery
- Restart affected pods
- Check NetworkPolicy / CNI
