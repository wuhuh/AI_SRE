package com.aisre.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 红线 41：tool-server 在没有 docker.sock / 非 in-cluster 时返回
 * 200 + {"dryRun": true}——什么都没执行。旧实现只看 statusCode 2xx 就判 SUCCESS，
 * 把 Incident 推进到 VERIFYING 并触发验证，k8s 形态下所有修复都是「假成功」。
 * 这些用例锁住「dryRun 必须被识别为未执行」这条契约。
 */
class RemediationDryRunTest {

    @Test
    void fastApiCompactFormatIsDetected() {
        // FastAPI 默认 separators 无空格——真实响应长这样，字符串匹配会漏判
        assertTrue(RemediationExecutor.isDryRun(
                "{\"action\":\"scale_deployment\",\"namespace\":\"default\",\"params\":{},\"dryRun\":true}"));
    }

    @Test
    void dryRunResponseIsDetected() {
        assertTrue(RemediationExecutor.isDryRun(
                "{\"action\":\"restart_pod\",\"namespace\":\"default\",\"params\":{},\"dryRun\":true}"));
    }

    @Test
    void realExecutionIsNotDryRun() {
        assertFalse(RemediationExecutor.isDryRun(
                "{\"action\":\"restart_pod\",\"executed\":true,\"detail\":\"restarted container\"}"));
        assertTrue(RemediationExecutor.isExecuted(
                "{\"action\":\"restart_pod\",\"executed\":true,\"detail\":\"restarted container\"}"));
    }

    @Test
    void dryRunBodyIsNotCountedAsExecuted() {
        assertFalse(RemediationExecutor.isExecuted("{\"dryRun\":true}"));
    }

    @Test
    void malformedBodyFallsBackToStatusCodePath() {
        assertFalse(RemediationExecutor.isDryRun("not-json"));
        assertFalse(RemediationExecutor.isExecuted("not-json"));
    }

    @Test
    void unknownOutcomeIsDetected() {
        // 文档 7.6/10.10：重放命中 IN_FLIGHT 记录 → UNKNOWN 待对账，不能猜成败
        assertTrue(RemediationExecutor.isUnknownOutcome(
                "{\"action\":\"restart_pod\",\"duplicate\":true,\"status\":\"UNKNOWN\"}"));
        assertFalse(RemediationExecutor.isUnknownOutcome(
                "{\"action\":\"restart_pod\",\"executed\":true,\"status\":\"SUCCEEDED\"}"));
        assertFalse(RemediationExecutor.isUnknownOutcome(
                "{\"dryRun\":true,\"status\":\"NOT_EXECUTED\"}"));
        assertFalse(RemediationExecutor.isUnknownOutcome(null));
    }

    @Test
    void nullAndEmptyAreNotDryRun() {
        assertFalse(RemediationExecutor.isDryRun(null));
        assertFalse(RemediationExecutor.isDryRun(""));
    }
}
