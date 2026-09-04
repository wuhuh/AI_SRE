package com.aisre.api.dto;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;

import java.time.Instant;

public record IncidentResponse(
        Long id,
        String service,
        IncidentStatus status,
        String severity,
        String summary,
        String rootCause,
        String recommendedActions,
        Double confidence,
        Instant startedAt,
        Instant resolvedAt,
        int alertCount
) {
    public static IncidentResponse from(Incident incident) {
        return new IncidentResponse(
                incident.getId(),
                incident.getService(),
                incident.getStatus(),
                incident.getSeverity(),
                incident.getSummary(),
                incident.getRootCause(),
                incident.getRecommendedActions(),
                incident.getConfidence(),
                incident.getStartedAt(),
                incident.getResolvedAt(),
                incident.getAlertCount()
        );
    }
}