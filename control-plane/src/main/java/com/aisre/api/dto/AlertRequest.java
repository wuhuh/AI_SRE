package com.aisre.api.dto;

import java.time.Instant;
import java.util.Map;

public record AlertRequest(
        String service,
        String alertName,
        String resource,
        String severity,
        String summary,
        Map<String, String> labels,
        Instant receivedAt
) {
}