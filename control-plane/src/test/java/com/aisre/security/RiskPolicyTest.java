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
}
