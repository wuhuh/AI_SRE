package com.aisre.api.dto;

import java.util.List;
import java.util.Map;

/**
 * P0-07: Alertmanager webhook v4 契约（字段对齐 prometheus/alertmanager 的
 * POST /api/v2/alerts 回调体；只声明本项目消费的字段，其余由 Jackson 忽略）。
 */
public record AlertmanagerWebhook(
        String version,
        String status,
        List<AlertmanagerAlert> alerts
) {

    public record AlertmanagerAlert(
            String status,
            Map<String, String> labels,
            Map<String, String> annotations,
            String startsAt,
            String endsAt,
            String fingerprint
    ) {
    }
}
