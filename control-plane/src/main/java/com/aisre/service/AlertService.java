package com.aisre.service;

import com.aisre.api.dto.AlertRequest;
import com.aisre.domain.Alert;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.AlertRepository;
import com.aisre.repo.IncidentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
public class AlertService {

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
            agentJobProducer.sendDiagnosisTask(incident.getId());
        }

        alert.setIncidentId(incident.getId());
        alertRepository.save(alert);
        auditService.record(incident.getId(), "alertmanager", "ALERT_INGESTED",
                "fingerprint=" + fingerprint + ", duplicate=" + !firstSeen);
        eventService.publish(incident.getId(), "ALERT_INGESTED", new AlertResult(incident.getId(), !firstSeen));
        return new AlertResult(incident.getId(), !firstSeen);
    }

    public Optional<Incident> findActiveIncident(String service) {
        Instant since = Instant.now().minus(AGGREGATION_WINDOW);
        List<Incident> candidates = incidentRepository.findByServiceContainingIgnoreCaseOrderByStartedAtDesc(service);
        return candidates.stream()
                .filter(i -> i.getStartedAt().isAfter(since))
                .filter(i -> i.getStatus() == IncidentStatus.DETECTED
                        || i.getStatus() == IncidentStatus.TRIAGING
                        || i.getStatus() == IncidentStatus.DIAGNOSING)
                .findFirst();
    }

    public static String fingerprint(String service, String alertName, String resource) {
        return service + ":" + alertName + ":" + resource;
    }

    public record AlertResult(Long incidentId, boolean duplicate) {
    }
}