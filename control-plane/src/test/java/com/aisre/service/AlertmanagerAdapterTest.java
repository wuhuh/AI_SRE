package com.aisre.service;

import com.aisre.api.dto.AlertRequest;
import com.aisre.api.dto.AlertmanagerWebhook;
import com.aisre.domain.Alert;
import com.aisre.domain.Incident;
import com.aisre.repo.AlertRepository;
import com.aisre.repo.IncidentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

/**
 * P0-07: Alertmanager webhook v4 契约适配 —— 真实 payload 结构
 * （alerts[].labels/annotations/status/startsAt）映射为内部扁平请求。
 */
class AlertmanagerAdapterTest {

    private AlertService alertService;
    private AlertmanagerAdapter adapter;

    @BeforeEach
    void setUp() {
        AlertRepository alertRepository = Mockito.mock(AlertRepository.class);
        IncidentRepository incidentRepository = Mockito.mock(IncidentRepository.class);
        AgentJobProducer producer = Mockito.mock(AgentJobProducer.class);
        AuditService auditService = Mockito.mock(AuditService.class);
        IncidentEventService eventService = Mockito.mock(IncidentEventService.class);
        when(alertRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        // 模拟 JPA 生成主键（真实库里 @GeneratedValue 会赋 id）
        when(incidentRepository.save(any())).thenAnswer(inv -> {
            Incident incident = inv.getArgument(0);
            if (incident.getId() == null) {
                incident.setId(1L);
            }
            return incident;
        });
        alertService = new AlertService(new InMemoryDeduplicationStore(),
                alertRepository, incidentRepository, producer, auditService, eventService);
        adapter = new AlertmanagerAdapter(alertService);
    }

    private static AlertmanagerWebhook.AlertmanagerAlert alert(String status, java.util.Map<String, String> labels,
                                                               java.util.Map<String, String> annotations) {
        return new AlertmanagerWebhook.AlertmanagerAlert(status, labels, annotations,
                "2026-09-05T02:00:00.000Z", "0001-01-01T00:00:00Z", "abc123");
    }

    @Test
    void realWebhookPayloadMapsContractFields() {
        // 典型 AM v4 payload：来自 PromQL 规则 + K8s 服务发现标签
        AlertmanagerWebhook webhook = new AlertmanagerWebhook("4", "firing", List.of(
                alert("firing",
                        java.util.Map.of("alertname", "ServiceLatencyHigh", "service", "payment-service",
                                "severity", "P1", "instance", "10.0.0.5:8080", "namespace", "prod"),
                        java.util.Map.of("summary", "p99 latency above 2s on payment-service"))));

        AlertmanagerAdapter.AdapterResult result = adapter.ingest(webhook);

        assertEquals(1, result.results().size());
        assertEquals(0, result.skippedResolved());
        assertEquals(1, result.results().get(0).incidentId());
        assertTrue(result.results().get(0).duplicate() == false);
    }

    @Test
    void duplicateAlertWithinTtlIsMarkedDuplicate() {
        AlertmanagerWebhook.AlertmanagerAlert am = alert("firing",
                java.util.Map.of("alertname", "HighErrorRate", "service", "order-service", "severity", "P1"),
                java.util.Map.of("summary", "5xx spike"));
        AlertmanagerWebhook webhook = new AlertmanagerWebhook("4", "firing", List.of(am));

        AlertmanagerAdapter.AdapterResult first = adapter.ingest(webhook);
        AlertmanagerAdapter.AdapterResult second = adapter.ingest(webhook);

        assertEquals(1, first.results().size());
        assertEquals(1, second.results().size());
        assertTrue(second.results().get(0).duplicate(), "5 分钟内重复告警应标记 duplicate");
        assertEquals(first.results().get(0).incidentId(), second.results().get(0).incidentId(),
                "去重后应聚合到同一 incident");
    }

    @Test
    void resolvedAlertsAreSkipped() {
        AlertmanagerWebhook webhook = new AlertmanagerWebhook("4", "firing", List.of(
                alert("resolved", java.util.Map.of("alertname", "HighLatency", "service", "s"), java.util.Map.of()),
                alert("firing", java.util.Map.of("alertname", "HighLatency", "service", "s"), java.util.Map.of())));
        AlertmanagerAdapter.AdapterResult result = adapter.ingest(webhook);
        assertEquals(1, result.results().size());
        assertEquals(1, result.skippedResolved());
    }

    @Test
    void missingLabelsFallBackToUnknownContract() {
        AlertRequest mapped = AlertmanagerAdapter.toAlertRequest(
                alert("firing", java.util.Map.of(), java.util.Map.of()));
        assertEquals("unknown", mapped.service());
        assertEquals("unknown", mapped.alertName());
        assertEquals("P2", mapped.severity());
        assertEquals("unknown", mapped.summary());
    }

    @Test
    void nullAlertsListDoesNotCrash() {
        AlertmanagerAdapter.AdapterResult result = adapter.ingest(new AlertmanagerWebhook("4", "firing", null));
        assertEquals(0, result.results().size());
        assertEquals(0, result.skippedResolved());
    }
}
