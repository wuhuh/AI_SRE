package com.aisre.api.dto;

import java.util.List;

public record DiagnosisRequest(
        String rootCause,
        Double confidence,
        List<EvidenceDTO> evidence,
        List<String> recommendedActions,
        List<ToolCallDTO> toolCalls,
        Long taskId
) {
}
