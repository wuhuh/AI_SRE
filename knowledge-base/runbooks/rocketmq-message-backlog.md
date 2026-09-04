# RocketMQ Message Backlog

## Symptoms
- Consumer lag increases
- Order processing delayed
- RocketMQ dashboard shows backlog

## Checks
1. `query_prometheus` rocketmq_consumer_lag
2. `query_logs` consumer errors
3. inspect consumer group status

## Recovery
- Scale consumers
- Fix poison messages
- Reset consumer offset if safe
