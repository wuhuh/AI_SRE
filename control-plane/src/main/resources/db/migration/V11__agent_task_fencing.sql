-- 文档《独立修订版》6.7 改进设计：fencing（旧执行者隔离）+ 11.6 重诊退避
--
-- claim_epoch：每次成功 claim 原子 +1。worker 后续所有业务写入
-- （complete / fail / diagnosis 回写）必须携带本次认领的 epoch，
-- 接收端同时校验 status + claimed_by + claim_epoch —— 旧世代写入被拒绝。
-- 递增序号（而非随机 token）让下游可以拒绝比已见世代更旧的请求。
ALTER TABLE agent_task ADD COLUMN claim_epoch INT NOT NULL DEFAULT 0;

-- not_before：任务最早可被领取时间（重诊退避）。QUEUED 但未到时间的任务
-- 不进入 pending 候选，避免上一轮刚失败就立刻原样重跑。
ALTER TABLE agent_task ADD COLUMN not_before TIMESTAMPTZ;
