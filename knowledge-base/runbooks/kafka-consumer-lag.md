# Kafka Consumer Lag (analog for RocketMQ)

## Symptoms
- consumer lag high
- events delayed
- processing backlog

## Checks
1. consumer group offset
2. `query_logs` consumer errors
3. producer throughput

## Recovery
- Scale consumers
- optimize processing
- skip poison messages if safe
