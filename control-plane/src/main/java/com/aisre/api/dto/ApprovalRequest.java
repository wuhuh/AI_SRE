package com.aisre.api.dto;

import java.util.Map;

public record ApprovalRequest(
        String decision,
        String operator,
        String comment,
        Map<String, Object> context
) {
}