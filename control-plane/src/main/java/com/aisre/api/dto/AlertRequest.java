package com.aisre.api.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.Instant;
import java.util.Map;

public record AlertRequest(
        @NotBlank String service,
        @NotBlank String alertName,
        String resource,
        String severity,
        String summary,
        Map<String, String> labels,
        Instant receivedAt
) {
}
