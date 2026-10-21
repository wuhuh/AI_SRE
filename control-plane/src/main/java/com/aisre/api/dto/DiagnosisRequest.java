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
        Long taskId,
        // 文档 6.7 fencing：worker 身份与本次认领的世代。
        // 可选——同步 API 路径（不走任务认领）不带这两个字段，跳过校验；
        // 带了 taskId 的异步主路径必须携带，接收端原子校验现任持有者。
        String workerId,
        Integer claimEpoch,
        // Agent 端诊断状态：ROOT_CAUSE_FOUND / UNKNOWN / TIMEOUT。
        // 旧客户端不传时由 rootCause 推导，保持向后兼容。
        String status,
        String reasonCode,
        List<String> candidateRootCauses,
        Boolean fallbackUsed,
        Integer llmInputTokens,
        Integer llmOutputTokens
) {
}
