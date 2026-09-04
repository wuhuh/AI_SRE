-- AI SRE initial schema
CREATE TABLE IF NOT EXISTS incident (
    id BIGSERIAL PRIMARY KEY,
    service VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    summary VARCHAR(2048),
    root_cause VARCHAR(2048),
    recommended_actions VARCHAR(4096),
    confidence DOUBLE PRECISION,
    started_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    report TEXT,
    alert_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_incident_status ON incident(status);
CREATE INDEX IF NOT EXISTS idx_incident_service ON incident(service);
CREATE INDEX IF NOT EXISTS idx_incident_started_at ON incident(started_at);

CREATE TABLE IF NOT EXISTS alert (
    id BIGSERIAL PRIMARY KEY,
    fingerprint VARCHAR(128) NOT NULL,
    service VARCHAR(128) NOT NULL,
    alert_name VARCHAR(128) NOT NULL,
    resource VARCHAR(256) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    summary VARCHAR(2048),
    raw_body TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    incident_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_alert_fingerprint ON alert(fingerprint);
CREATE INDEX IF NOT EXISTS idx_alert_received_at ON alert(received_at);
CREATE INDEX IF NOT EXISTS idx_alert_incident_id ON alert(incident_id);

CREATE TABLE IF NOT EXISTS agent_task (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    result_json TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_task_incident ON agent_task(incident_id);
CREATE INDEX IF NOT EXISTS idx_agent_task_status ON agent_task(status);
CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_task_idempotency ON agent_task(idempotency_key);

CREATE TABLE IF NOT EXISTS agent_step (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    incident_id BIGINT NOT NULL,
    step_order INTEGER NOT NULL,
    step_type VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_step_task ON agent_step(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_step_incident ON agent_step(incident_id);

CREATE TABLE IF NOT EXISTS evidence (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    task_id BIGINT,
    source VARCHAR(64) NOT NULL,
    evidence_key VARCHAR(128) NOT NULL,
    content TEXT NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_incident ON evidence(incident_id);
CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id);

CREATE TABLE IF NOT EXISTS tool_call (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    task_id BIGINT,
    tool_name VARCHAR(128) NOT NULL,
    risk_level VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    arguments_json TEXT NOT NULL,
    result_summary TEXT,
    duration_ms BIGINT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tool_call_incident ON tool_call(incident_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_task ON tool_call(task_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_name ON tool_call(tool_name);

CREATE TABLE IF NOT EXISTS approval (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    action_type VARCHAR(128) NOT NULL,
    action_payload TEXT NOT NULL,
    status VARCHAR(16) NOT NULL,
    requested_by VARCHAR(64),
    decided_by VARCHAR(64),
    comment VARCHAR(1024),
    created_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approval_incident ON approval(incident_id);
CREATE INDEX IF NOT EXISTS idx_approval_status ON approval(status);

CREATE TABLE IF NOT EXISTS remediation_action (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL,
    tool_name VARCHAR(128) NOT NULL,
    arguments_json TEXT NOT NULL,
    status VARCHAR(16) NOT NULL,
    approval_id BIGINT,
    result_summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    executed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_remediation_incident ON remediation_action(incident_id);
CREATE INDEX IF NOT EXISTS idx_remediation_status ON remediation_action(status);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT,
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    detail TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_log(incident_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);

CREATE TABLE IF NOT EXISTS runbook (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    service VARCHAR(128),
    tags VARCHAR(512),
    content TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runbook_service ON runbook(service);
CREATE INDEX IF NOT EXISTS idx_runbook_tags ON runbook(tags);

CREATE TABLE IF NOT EXISTS evaluation_case (
    id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(128) NOT NULL,
    fault_type VARCHAR(128) NOT NULL,
    service VARCHAR(128) NOT NULL,
    expected_root_cause VARCHAR(1024) NOT NULL,
    expected_evidence TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_fault_type ON evaluation_case(fault_type);
CREATE INDEX IF NOT EXISTS idx_eval_service ON evaluation_case(service);