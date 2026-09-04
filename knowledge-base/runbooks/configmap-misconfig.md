# ConfigMap Misconfiguration

## Symptoms
- service fails to start
- invalid env
- pod CrashLoopBackOff

## Checks
1. `get_pod_logs`
2. `get_deployment` env
3. `get_events`

## Recovery
- Correct ConfigMap
- Rollout restart
