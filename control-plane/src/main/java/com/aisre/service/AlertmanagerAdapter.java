package com.aisre.service;

import com.aisre.api.dto.AlertRequest;
import com.aisre.api.dto.AlertmanagerWebhook;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * P0-07 (FI-01 一期): 把 Alertmanager webhook 的 labels/annotations 契约
 * 适配为内部扁平 AlertRequest，复用既有的去重/聚合/任务派发链路。
 */
@Service
public class AlertmanagerAdapter {

    private static final Logger log = LoggerFactory.getLogger(AlertmanagerAdapter.class);

    private final AlertService alertService;

    public AlertmanagerAdapter(AlertService alertService) {
        this.alertService = alertService;
    }

    public record AdapterResult(List<AlertService.AlertResult> results, int skippedResolved) {
    }

    public AdapterResult ingest(AlertmanagerWebhook webhook) {
        List<AlertService.AlertResult> results = new ArrayList<>();
        int skipped = 0;
        for (AlertmanagerWebhook.AlertmanagerAlert alert : webhook.alerts() == null
                ? List.<AlertmanagerWebhook.AlertmanagerAlert>of()
                : webhook.alerts()) {
            // resolved 恢复事件的处理（自动 RESOLVED）是 FI-03 范围；这里只消费 firing
            String status = alert.status() != null ? alert.status() : webhook.status();
            if ("resolved".equalsIgnoreCase(status)) {
                skipped++;
                continue;
            }
            try {
                results.add(alertService.ingest(toAlertRequest(alert)));
            } catch (Exception e) {
                log.warn("failed to ingest alertmanager alert {}: {}", alert.fingerprint(), e.getMessage());
            }
        }
        return new AdapterResult(results, skipped);
    }

    static AlertRequest toAlertRequest(AlertmanagerWebhook.AlertmanagerAlert alert) {
        Map<String, String> labels = alert.labels() == null ? Map.of() : alert.labels();
        Map<String, String> annotations = alert.annotations() == null ? Map.of() : alert.annotations();
        String alertName = firstNonBlank(labels.get("alertname"), "unknown");
        String service = firstNonBlank(labels.get("service"), labels.get("service_name"),
                labels.get("job"), "unknown");
        // P2-CP-23 收尾：非标准告警（无 instance/pod）不再因 resource=null 被 DB 拒收
        String resource = firstNonBlank(labels.get("instance"), labels.get("pod"),
                labels.get("resource"), labels.get("service"), "");
        String severity = firstNonBlank(labels.get("severity"), "P2");
        String summary = firstNonBlank(annotations.get("summary"), annotations.get("description"), alertName);
        return new AlertRequest(service, alertName, resource, severity, summary, labels, parseStartsAt(alert));
    }

    private static Instant parseStartsAt(AlertmanagerWebhook.AlertmanagerAlert alert) {
        if (alert.startsAt() == null || alert.startsAt().isBlank()) {
            return null;
        }
        try {
            return Instant.parse(alert.startsAt());
        } catch (DateTimeParseException e) {
            return null;
        }
    }

    private static String firstNonBlank(String... candidates) {
        for (String candidate : candidates) {
            if (candidate != null && !candidate.isBlank()) {
                return candidate;
            }
        }
        return null;
    }
}
