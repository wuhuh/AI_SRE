package com.aisre.service;

import com.aisre.domain.Approval;
import com.aisre.domain.Incident;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

/**
 * 文档 10.4：审批绑定不可变动作计划。
 * planDigest = SHA-256(action + body)；同一计划摘要稳定，参数/目标漂移则摘要变化，
 * 执行前比对不匹配即拒绝（批准的对象 ≠ 实际执行的对象）。
 */
class RemediationPlanDigestTest {

    private Incident incident(String service) {
        Incident incident = new Incident();
        incident.setService(service);
        return incident;
    }

    private Approval approval(String action, String payload) {
        return new Approval(1L, action, payload, com.aisre.domain.ApprovalStatus.APPROVED, "test", null);
    }

    @Test
    void digestIsStableForSamePlan() {
        String body = RemediationExecutor.buildExecutionBody(
                "restart_pod", approval("restart_pod", "{}"),
                incident("order-service"), "rem-1").orElseThrow();
        String d1 = RemediationExecutor.planDigest("restart_pod", body);
        String d2 = RemediationExecutor.planDigest("restart_pod", body);
        assertEquals(d1, d2);
        assertEquals(64, d1.length());
    }

    @Test
    void digestChangesWhenTargetChanges() {
        // 文档 10.4 教学反例：批准时是 order-service，执行时目标变成 payment-service
        String approved = RemediationExecutor.buildExecutionBody(
                "restart_pod", approval("restart_pod", "{}"),
                incident("order-service"), "rem-1").orElseThrow();
        String actual = RemediationExecutor.buildExecutionBody(
                "restart_pod", approval("restart_pod", "{}"),
                incident("payment-service"), "rem-1").orElseThrow();
        assertNotEquals(RemediationExecutor.planDigest("restart_pod", approved),
                RemediationExecutor.planDigest("restart_pod", actual));
    }

    @Test
    void digestChangesWhenParamsChange() {
        String five = RemediationExecutor.buildExecutionBody(
                "scale_deployment",
                approval("scale_deployment", "{\"replicas\":5}"),
                incident("payment-service"), "rem-1").orElseThrow();
        String three = RemediationExecutor.buildExecutionBody(
                "scale_deployment",
                approval("scale_deployment", "{\"replicas\":3}"),
                incident("payment-service"), "rem-1").orElseThrow();
        assertNotEquals(RemediationExecutor.planDigest("scale_deployment", five),
                RemediationExecutor.planDigest("scale_deployment", three));
    }

    @Test
    void actionNameIsPartOfDigest() {
        String body = RemediationExecutor.buildExecutionBody(
                "restart_pod", approval("restart_pod", "{}"),
                incident("x"), "rem-1").orElseThrow();
        assertNotEquals(RemediationExecutor.planDigest("restart_pod", body),
                RemediationExecutor.planDigest("restart_service", body));
    }
}
