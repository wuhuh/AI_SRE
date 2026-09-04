package com.aisre.api.dto;

import com.aisre.domain.IncidentStatus;

public record IncidentTransitionRequest(IncidentStatus status) {
}