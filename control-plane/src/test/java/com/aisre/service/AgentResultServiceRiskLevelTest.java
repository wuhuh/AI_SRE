package com.aisre.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * 红线 42：跨服务契约对 riskLevel 值域零约束。旧实现缺省成 READ_ONLY（最宽松），
 * 上游漏发一个字段就让高风险调用看起来像只读，审批可能被绕过。
 * 现在只接受三个合法值，其余一律 fail-closed 为 HIGH_RISK。
 */
class AgentResultServiceRiskLevelTest {

    @Test
    void acceptsTheThreeContractValues() {
        assertEquals("READ_ONLY", AgentResultService.normalizeRiskLevel("READ_ONLY", "query_logs"));
        assertEquals("LOW_RISK", AgentResultService.normalizeRiskLevel("LOW_RISK", "restart_pod"));
        assertEquals("HIGH_RISK", AgentResultService.normalizeRiskLevel("HIGH_RISK", "scale_deployment"));
    }

    @Test
    void normalizesCaseAndWhitespace() {
        assertEquals("READ_ONLY", AgentResultService.normalizeRiskLevel(" read_only ", "query_logs"));
    }

    @Test
    void missingRiskLevelFailsClosedToHighRisk() {
        // 旧行为是 READ_ONLY —— 这正是「审批被绕过」的入口
        assertEquals("HIGH_RISK", AgentResultService.normalizeRiskLevel(null, "scale_deployment"));
        assertEquals("HIGH_RISK", AgentResultService.normalizeRiskLevel("", "scale_deployment"));
        assertEquals("HIGH_RISK", AgentResultService.normalizeRiskLevel("   ", "scale_deployment"));
    }

    @Test
    void unknownRiskLevelFailsClosedToHighRisk() {
        assertEquals("HIGH_RISK", AgentResultService.normalizeRiskLevel("MEDIUM", "delete_pod"));
        assertEquals("HIGH_RISK", AgentResultService.normalizeRiskLevel("CRITICAL", "delete_pod"));
    }
}
