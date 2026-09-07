-- P1-MQ-03: 毒任务重试计数（租约回收时 +1，达上限转 DEAD＝DLQ 等价物）
ALTER TABLE agent_task ADD COLUMN attempts INT NOT NULL DEFAULT 0;
