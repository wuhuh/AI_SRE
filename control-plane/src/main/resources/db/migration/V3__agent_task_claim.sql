-- P1-MQ-02: 任务领取/租约字段
ALTER TABLE agent_task ADD COLUMN claimed_by VARCHAR(64);
ALTER TABLE agent_task ADD COLUMN claimed_at TIMESTAMP;
