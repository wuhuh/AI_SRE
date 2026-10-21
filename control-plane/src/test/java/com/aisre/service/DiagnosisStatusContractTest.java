package com.aisre.service;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 文档 8.5/8.6：Agent 的 UNKNOWN/TIMEOUT 不能被 CP 当成 ROOT_CAUSE_FOUND。
 * 未知状态一律 fail-closed 为 UNKNOWN，动作建议由调用方抑制。
 */
class DiagnosisStatusContractTest {

    @Test
    void validRootWithLegacyPayloadIsRootCauseFound() {
        assertEquals("ROOT_CAUSE_FOUND",
                AgentResultService.normalizeDiagnosisStatus(null, "slow_sql", false));
        assertEquals("ROOT_CAUSE_FOUND",
                AgentResultService.normalizeDiagnosisStatus(" root_cause_found ", "slow_sql", false));
    }

    @Test
    void unknownAndTimeoutArePreserved() {
        assertEquals("UNKNOWN",
                AgentResultService.normalizeDiagnosisStatus("UNKNOWN", "slow_sql", false));
        assertEquals("TIMEOUT",
                AgentResultService.normalizeDiagnosisStatus("timeout", "slow_sql", false));
    }

    @Test
    void invalidLabelOrUnknownRootCannotMasqueradeAsFound() {
        assertEquals("UNKNOWN",
                AgentResultService.normalizeDiagnosisStatus(null, "unknown", false));
        assertEquals("UNKNOWN",
                AgentResultService.normalizeDiagnosisStatus("ROOT_CAUSE_FOUND", "unknown", true));
    }

    @Test
    void unrecognizedStatusFailsClosed() {
        assertEquals("UNKNOWN",
                AgentResultService.normalizeDiagnosisStatus("PARTIAL", "slow_sql", false));
        assertEquals("UNKNOWN",
                AgentResultService.normalizeDiagnosisStatus("banana", "slow_sql", false));
    }

    @Test
    void candidatesAreTrimmedJoinedAndCapped() {
        assertEquals("slow_sql,cpu_saturation",
                AgentResultService.joinCandidates(Arrays.asList(" slow_sql ", "", null, "cpu_saturation")));
        assertNull(AgentResultService.joinCandidates(null));
        assertNull(AgentResultService.joinCandidates(List.of(" ", "")));

        String longLabel = "x".repeat(2000);
        String joined = AgentResultService.joinCandidates(List.of(longLabel));
        assertTrue(joined.length() <= 1024);
    }

    @Test
    void blankReasonBecomesNull() {
        assertNull(AgentResultService.blankToNull("  "));
        assertEquals("model_unknown", AgentResultService.blankToNull(" model_unknown "));
    }
}
