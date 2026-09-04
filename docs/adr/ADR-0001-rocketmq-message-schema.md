# ADR-0001: RocketMQ 任务消息 Schema

## Context

当前 Control Plane 已向 RocketMQ Topic `aisre-agent-task` 发送任务消息，但 Agent Runtime 仍以 HTTP polling 为主要消费方式。为了使 RocketMQ 成为正式主链路，需要稳定消息 Schema 并支持幂等消费。

## Problem

- 消息结构不统一
- At-least-once 投递可能导致重复执行
- 缺少 eventId 无法幂等

## Decision

使用以下 JSON Schema 作为任务消息标准：

```json
{
  "eventId": "",
  "taskId": "",
  "incidentId": "",
  "type": "DIAGNOSIS",
  "createdAt": "",
  "traceId": "",
  "version": 1
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| eventId | string | 是 | 全局唯一事件 ID |
| taskId | string | 是 | AgentTask ID |
| incidentId | string | 是 | Incident ID |
| type | string | 是 | `DIAGNOSIS` / `VERIFICATION` |
| createdAt | string | 是 | ISO-8601 时间 |
| traceId | string | 否 | Trace ID |
| version | int | 是 | Schema 版本，当前 1 |

## Alternatives

- 继续 HTTP polling：开发调试方便，但不是正式生产链路。
- 使用 Kafka：增加复杂度，当前 RocketMQ 已存在。

## Trade-offs

- 需要 Control Plane Producer 发送结构化 JSON。
- 需要 Agent Consumer 解析并幂等。
- HTTP polling 保留为 development fallback。

## Migration

1. Control Plane `RocketMqAgentJobProducer` 发送结构化 JSON。
2. Agent Runtime `mq_consumer.py` 解析 eventId 并写入 Idempotency Store。
3. 保留 `consumer.py` HTTP polling 作为 fallback。