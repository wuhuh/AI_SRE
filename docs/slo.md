# SLO / SLI

## Demo Services SLO

| Service | Availability | P95 Latency | Error Rate |
| --- | --- | --- | --- |
| api-gateway | >= 99% | < 500ms | < 1% |
| order-service | >= 99% | < 500ms | < 1% |
| inventory-service | >= 99% | < 500ms | < 1% |
| payment-service | >= 99% | < 500ms | < 1% |

## SLI

- Availability = successful requests / total requests
- Latency = P95 of `http_request_duration_seconds`
- Error Rate = 5xx requests / total requests

## Prometheus

已增加 Alert Rules：

```text
HighErrorRate
HighLatency
ServiceDown
HighCPU
HighMemory
RedisPoolHigh
DatabasePoolHigh
RocketMQLagHigh
```

Prometheus 通过 Alertmanager Webhook 发送到：

```text
http://control-plane:8080/api/v1/alerts
```