package com.aisre.api.dto;

public record RemediationRequest(
        String toolName,
        String argumentsJson,
        String status,
        Long approvalId,
        String resultSummary
) {
}