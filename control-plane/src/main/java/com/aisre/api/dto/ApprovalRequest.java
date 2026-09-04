package com.aisre.api.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.Map;

public record ApprovalRequest(
        @NotBlank String decision,
        String operator,
        String comment,
        Map<String, Object> context
) {
}
