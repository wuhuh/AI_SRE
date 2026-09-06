package com.aisre.service;

import com.aisre.api.dto.AlertRequest;
import com.aisre.domain.Alert;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.AlertRepository;
import com.aisre.repo.IncidentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
public class AlertService {

    private static final Logger log = LoggerFactory.getLogger(AlertService.class);

    private static final Duration DEDUP_TTL = Duration.ofMinutes(5);
    private static final Duration AGGREGATION_WINDOW = Duration.ofMinutes(10);

    private final DeduplicationStore deduplicationStore;
    private final AlertRepository alertRepository;
    private final IncidentRepository incidentRepository;
    private final AgentJobProducer agentJobProducer;
    private final AuditService auditService;
    private final IncidentEventService eventService;

    public AlertService(DeduplicationStore deduplicationStore,
                        AlertRepository alertRepository,
                        IncidentRepository incidentRepository,
                        AgentJobProducer agentJobProducer,
                        AuditService auditService,
                        IncidentEventService eventService) {
        this.deduplicationStore = deduplicationStore;
        this.alertRepository = alertRepository;
        this.incidentRepository = incidentRepository;
        this.agentJobProducer = agentJobProducer;
        this.auditService = auditService;
        this.eventService = eventService;
    }

    @Transactional
    public AlertResult ingest(AlertRequest request) {
        String fingerprint = fingerprint(request.service(), request.alertName(), request.resource());
        boolean firstSeen = deduplicationStore.putIfAbsent(fingerprint, DEDUP_TTL);

        Instant receivedAt = request.receivedAt() != null ? request.receivedAt() : Instant.now();
        Alert alert = new Alert(
                fingerprint,
                request.service(),
                request.alertName(),
                request.resource(),
                request.severity(),
                request.summary() != null ? request.summary() : "",
                request.labels() != null ? request.labels().toString() : "",
                receivedAt
        );
        alertRepository.save(alert);

        // P1-CP-15: 重复告警真正被抑制——落 alert 行（留证据）但不重复计数、不追加
        // 摘要、不再触发任务。firstSeen=false 时只把告警挂到活跃 incident 上。
        if (!firstSeen) {
            Optional<Incident> active = findActiveIncident(request.service());
            if (active.isPresent()) {
                alert.setIncidentId(active.get().getId());
                alertRepository.save(alert);
                return new AlertResult(active.get().getId(), true);
            }
            // 活跃 incident 已不在（已被验证解决等）：视为新告警继续走完整链路
        }

        Optional<Incident> existing = findActiveIncident(request.service());
        Incident incident;
        if (existing.isPresent()) {
            incident = existing.get();
            incident.setAlertCount(incident.getAlertCount() + 1);
            String combined = incident.getSummary() + " | " + alert.getSummary();
            incident.setSummary(combined.length() > 2000 ? alert.getSummary() : combined);
            incident = incidentRepository.save(incident);
        } else {
            incident = new Incident(request.service(), request.severity(), alert.getSummary(), receivedAt);
            incident.setAlertCount(1);
            incident = incidentRepository.save(incident);
            // ponytail: 同服务不同告警并发创建的竞态窗口仍在（需要 partial unique
            // index 或行锁才根治）；fingerprint 去重已挡住同指纹重复，窗口足够窄
            agentJobProducer.sendDiagnosisTask(incident.getId());
        }

        alert.setIncidentId(incident.getId());
        alertRepository.save(alert);
        log.info("alert ingested: fingerprint={}, duplicate={}, incidentId={}, alertName={}",
                fingerprint, !firstSeen, incident.getId(), request.alertName());
        auditService.record(incident.getId(), "alertmanager", "ALERT_INGESTED",
                "fingerprint=" + fingerprint + ", duplicate=" + !firstSeen);
        eventService.publish(incident.getId(), "ALERT_INGESTED", new AlertResult(incident.getId(), !firstSeen));
        return new AlertResult(incident.getId(), !firstSeen);
    }

    public Optional<Incident> findActiveIncident(String service) {
        // P1-CP-09: 精确匹配 + 状态/时间窗条件下推到 SQL（原 containing 忽略大小写
        // 且把 payment-service-v2 误聚合进 payment-service）
        Instant since = Instant.now().minus(AGGREGATION_WINDOW);
        List<Incident> candidates = incidentRepository
                .findByServiceAndStatusInAndStartedAtAfterOrderByStartedAtDesc(
                        service,
                        List.of(IncidentStatus.DETECTED, IncidentStatus.TRIAGING, IncidentStatus.DIAGNOSING),
                        since);
        return candidates.stream().findFirst();
    }

    public static String fingerprint(String service, String alertName, String resource) {
        return service + ":" + alertName + ":" + resource;
    }

    public record AlertResult(Long incidentId, boolean duplicate) {
    }
}