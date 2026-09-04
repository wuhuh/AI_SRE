# Thread Pool Exhausted

## Symptoms
- Tomcat/Jetty threads max
- Requests queued
- logs "Thread pool exhausted"

## Checks
1. `query_prometheus` tomcat_threads_busy
2. `query_logs` "thread pool"
3. `query_trace` queued spans

## Recovery
- Scale pods
- Tune thread pool and queue size
- Fix blocking calls
