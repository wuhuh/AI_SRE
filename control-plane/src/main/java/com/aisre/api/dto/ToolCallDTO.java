package com.aisre.api.dto;

import java.time.Instant;

public record ToolCallDTO(
        String toolName,
        String argumentsJson,
        String status,
        String resultSummary,
        Long durationMs,
        String error,
        Instant createdAt
) {
}