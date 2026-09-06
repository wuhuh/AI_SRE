-- P1-CP-07/08: outbox 投递状态 + 幂等键唯一
ALTER TABLE agent_task ADD COLUMN mq_status VARCHAR(16) NOT NULL DEFAULT 'PENDING';
ALTER TABLE agent_task ADD COLUMN mq_attempts INT NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_task_idem ON agent_task(idempotency_key);
