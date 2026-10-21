package com.aisre.security;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RiskPolicyTest {

    @Test
    void unknownActionIsHighRiskByDefault() {
        // P0-04: fail-closed —— 策略表外动作不能自动执行
        assertEquals(RiskPolicy.RiskLevel.HIGH_RISK, RiskPolicy.classify("purge_database"));
        assertEquals(RiskPolicy.RiskLevel.HIGH_RISK, RiskPolicy.classify(null));
        assertTrue(RiskPolicy.requiresApproval("drop_table_users"));
    }

    @Test
    void knownActionsKeepTheirLevels() {
        assertEquals(RiskPolicy.RiskLevel.LOW_RISK, RiskPolicy.classify("restart_pod"));
        assertEquals(RiskPolicy.RiskLevel.HIGH_RISK, RiskPolicy.classify("scale_deployment"));
        assertFalse(RiskPolicy.requiresApproval("clear_redis_cache"));
    }

    @Test
    void onlyCanonicalActionNamesEnterApprovalPipeline() {
        assertTrue(RiskPolicy.isKnownAction("restart_pod"));
        assertTrue(RiskPolicy.isKnownAction(" SCALE_DEPLOYMENT "));
        // LLM 的整句建议不是动作名，不能生成 approval（E2E 中曾触发 varchar(128) 溢出）
        assertFalse(RiskPolicy.isKnownAction(
                "Please restart the payment service and inspect the Redis connection pool"));
        assertFalse(RiskPolicy.isKnownAction(null));
    }
}
