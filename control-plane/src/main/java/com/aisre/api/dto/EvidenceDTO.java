package com.aisre.api.dto;

import java.time.Instant;

public record EvidenceDTO(
        String source,
        String key,
        String content,
        Instant timestamp,
        String query,
        String timeRange
) {
}
