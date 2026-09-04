package com.aisre.security;

import java.util.Map;
import java.util.Set;

/**
 * Static risk policy. Risk is determined by explicit action definitions, not by
 * LLM judgment. The LLM may only propose an action; this policy decides whether
 * human approval is required.
 */
public final class RiskPolicy {

    public enum RiskLevel {
        READ_ONLY,
        LOW_RISK,
        HIGH_RISK
    }

    private static final Map<String, RiskLevel> ACTION_RISK = Map.ofEntries(
            Map.entry("restart_pod", RiskLevel.LOW_RISK),
            Map.entry("scale_deployment", RiskLevel.HIGH_RISK),
            Map.entry("delete_pod", RiskLevel.HIGH_RISK),
            Map.entry("clear_redis_cache", RiskLevel.LOW_RISK),
            Map.entry("increase_redis_maxclients", RiskLevel.HIGH_RISK),
            Map.entry("increase_db_pool_size", RiskLevel.HIGH_RISK),
            Map.entry("disable_fault", RiskLevel.LOW_RISK),
            Map.entry("rollback_deployment", RiskLevel.HIGH_RISK),
            Map.entry("restart_service", RiskLevel.LOW_RISK)
    );

    private RiskPolicy() {
    }

    public static RiskLevel classify(String action) {
        if (action == null) {
            return RiskLevel.HIGH_RISK;
        }
        String normalized = action.trim().toLowerCase();
        // P0-04: fail-closed —— 策略表之外的未知动作一律按 HIGH_RISK 处理，
        // 走人工审批而不是自动执行（旧实现 getOrDefault(LOW_RISK) 是放水）。
        return ACTION_RISK.getOrDefault(normalized, RiskLevel.HIGH_RISK);
    }

    public static boolean requiresApproval(String action) {
        return classify(action) == RiskLevel.HIGH_RISK;
    }
}