-- 文档 10.4：审批必须批准具体内容 —— 绑定不可变动作计划摘要。
-- 审批创建时解析出确定的执行计划（action + 参数 + 目标），算 SHA-256 摘要落库；
-- 执行时按同一规则重建计划并比对摘要，不一致 = 批准的对象与实际对象不同 → 拒绝执行。
-- 10.4 教学反例：审批时目标是实例 A，执行时名称已被复用为实例 B——只按名称执行，
-- 用户批准的对象与实际对象不同。摘要把「批准了什么」固化下来。
ALTER TABLE approval ADD COLUMN plan_digest VARCHAR(64);

-- 文档 6.5：lease_until 显式租约。claim 时写入 now+lease；持有者可携带
-- worker+claim_epoch 心跳续租（总时长受 startedAt+max 封顶）；
-- 回收器按 lease_until 判过期。存量行为（claimed_at+固定时长）保留为回退。
ALTER TABLE agent_task ADD COLUMN lease_until TIMESTAMPTZ;
