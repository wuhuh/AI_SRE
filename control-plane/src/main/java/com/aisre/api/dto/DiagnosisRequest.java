package com.aisre.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public record DiagnosisRequest(
        @NotBlank String rootCause,
        Double confidence,
        List<EvidenceDTO> evidence,
        List<String> recommendedActions,
        List<ToolCallDTO> toolCalls,
        Long taskId
) {
}
