# Order Service Latency

## Symptoms
- order-service P95 high
- inventory/payment downstream slow
- queue backlog

## Checks
1. `query_prometheus` http latency
2. `query_trace` order->inventory/payment spans
3. `query_logs` errors

## Recovery
- Scale order-service
- Increase downstream timeouts
