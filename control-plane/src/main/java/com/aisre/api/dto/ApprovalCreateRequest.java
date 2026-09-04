package com.aisre.api.dto;

public record ApprovalCreateRequest(
        Long incidentId,
        String actionType,
        String actionPayload,
        String requestedBy
) {
}