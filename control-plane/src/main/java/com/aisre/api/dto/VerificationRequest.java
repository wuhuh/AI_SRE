package com.aisre.api.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

public record VerificationRequest(
        @NotBlank String status,
        String detail,
        List<EvidenceDTO> evidence,
        Long taskId,
        // 文档 11.6：本回调验证的是哪一轮诊断的处置结果。
        // NOT_RECOVERED 时据此识别重放回调（事故轮次已推进过 → 跳过建轮）。
        // 可选——旧客户端不带时退回轮次键推算（存在极窄的重放窗口，见 saveVerification 注释）。
        Integer diagnosisRound
) {
}
