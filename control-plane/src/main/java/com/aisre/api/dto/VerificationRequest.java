package com.aisre.api.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record VerificationRequest(
        @NotBlank String status,
        String detail,
        List<EvidenceDTO> evidence,
        Long taskId
) {
}
