-- 文档 8.5/8.6：Agent 诊断状态与降级原因必须落库并可查询，
-- 不能只在 Agent 进程内存在。UNKNOWN / TIMEOUT 不冒充 root cause。
ALTER TABLE incident ADD COLUMN diagnosis_status VARCHAR(32);
ALTER TABLE incident ADD COLUMN reason_code VARCHAR(64);
ALTER TABLE incident ADD COLUMN candidate_root_causes VARCHAR(1024);
ALTER TABLE incident ADD COLUMN fallback_used BOOLEAN;
ALTER TABLE incident ADD COLUMN llm_input_tokens INTEGER;
ALTER TABLE incident ADD COLUMN llm_output_tokens INTEGER;
