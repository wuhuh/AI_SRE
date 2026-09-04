# Postmortem: Redis Connection Pool Exhausted (2024-06-01)

## Impact
Payment API P99 increased from 120ms to 3s for 25 minutes.

## Root Cause
A connection leak in payment service kept Redis connections open without release.

## Detection
Prometheus alerted on `redis_connected_clients > 0.9 * maxclients`.

## Resolution
Restarted payment-service; added connection leak guard.

## Action Items
- Add Redis client health check
- Set maxTotal with validation
