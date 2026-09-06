-- P1-CP-12: 审批过期语义
ALTER TABLE approval ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
-- 存量 PENDING 给一个从创建起 1 小时的宽限
UPDATE approval SET expires_at = created_at + interval '1 hour'
WHERE status = 'PENDING' AND expires_at IS NULL;
