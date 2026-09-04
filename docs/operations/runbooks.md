# Operations Runbooks

## Control Plane Down

1. Check container: `docker ps`
2. Restart: `docker compose restart control-plane`
3. Check logs: `docker logs aisre-control-plane-1 --tail 200`
4. Check DB/Redis/RocketMQ connectivity

## Agent Runtime Down

1. Restart: `docker compose restart agent-runtime`
2. Check logs
3. Check pending tasks: `GET /api/v1/tasks/pending`

## RocketMQ Backlog

1. Check topic: `mqadmin topicList`
2. Check consumer lag
3. Restart consumer or scale Agent Runtime

## PostgreSQL Unavailable

1. Check container: `docker ps`
2. Restart postgres
3. If data lost: `scripts/restore-db.ps1`

## Redis Unavailable

1. Restart Redis
2. Alert dedup will temporarily fail-open or fail-closed as configured

## Tool Server Error

1. Check logs
2. Verify approval token / execution token
3. Restart tool-server