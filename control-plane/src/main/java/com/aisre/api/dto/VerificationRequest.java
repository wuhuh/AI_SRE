package com.aisre.api.dto;

import java.util.List;

public record VerificationRequest(
        String status,
        String detail,
        List<EvidenceDTO> evidence
) {
}