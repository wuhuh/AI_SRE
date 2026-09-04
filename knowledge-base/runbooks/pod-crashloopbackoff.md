# Pod CrashLoopBackOff

## Symptoms
- Pod status CrashLoopBackOff
- Restart count increasing
- logs show startup error

## Checks
1. `get_pod`
2. `get_pod_logs`
3. `get_events`

## Recovery
- Fix configuration or resource limit
- Restart pod after fix
