package com.aisre.service;

import com.aisre.domain.Approval;
import com.aisre.domain.Incident;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RemediationExecutorBodyTest {

    private Incident incident(String service) {
        Incident incident = new Incident();
        incident.setService(service);
        return incident;
    }

    private Approval approval(String action, String payload) {
        Approval approval = new Approval(1L, action, payload, com.aisre.domain.ApprovalStatus.APPROVED, "test", null);
        return approval;
    }

    @Test
    void scaleBodyUsesRealServiceFromPayload() throws Exception {
        Optional<String> body = RemediationExecutor.buildExecutionBody(
                "scale_deployment",
                approval("scale_deployment", "{\"namespace\":\"prod\",\"deployment\":\"payment-service\",\"replicas\":5}"),
                incident("payment-service"), "rem-1");
        assertTrue(body.isPresent());
        // 文档 7.6：execution_id 随请求下发，tool-server 据此做操作幂等
        assertTrue(body.get().contains("\"execution_id\":\"rem-1\""));
        assertTrue(body.get().contains("\"deployment\":\"payment-service\""));
        assertTrue(body.get().contains("\"replicas\":5"));
        assertTrue(body.get().contains("\"namespace\":\"prod\""));
    }

    @Test
    void missingPayloadFieldsFallBackToIncidentService() throws Exception {
        Optional<String> body = RemediationExecutor.buildExecutionBody(
                "restart_pod", approval("restart_pod", "{}"), incident("order-service"), "rem-2");
        assertTrue(body.isPresent());
        assertTrue(body.get().contains("\"pod\":\"order-service\""));
    }

    @Test
    void unknownActionIsRefused() {
        // P0-04: default 兜底已删 —— 未知动作必须 fail-closed
        assertTrue(RemediationExecutor.buildExecutionBody(
                "purge_database", approval("purge_database", "{}"), incident("x"), null).isEmpty());
        assertTrue(RemediationExecutor.buildExecutionBody(
                null, approval(null, "{}"), incident("x"), null).isEmpty());
    }

    @Test
    void corruptedPayloadDoesNotCrash() throws Exception {
        Optional<String> body = RemediationExecutor.buildExecutionBody(
                "restart_pod", approval("restart_pod", "not-json{"), incident("db-service"), "rem-3");
        assertTrue(body.isPresent());
        assertTrue(body.get().contains("\"pod\":\"db-service\""));
        assertEquals(Optional.empty(), RemediationExecutor.buildExecutionBody(
                "increase_db_pool_size", approval("increase_db_pool_size", "{}"), incident("x"), null));
    }
}
