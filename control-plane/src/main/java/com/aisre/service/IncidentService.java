package com.aisre.service;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.IncidentRepository;
import com.aisre.state.IncidentStateMachine;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Service
public class IncidentService {

    private final IncidentRepository incidentRepository;
    private final AuditService auditService;
    private final IncidentEventService eventService;

    public IncidentService(IncidentRepository incidentRepository,
                           AuditService auditService,
                           IncidentEventService eventService) {
        this.incidentRepository = incidentRepository;
        this.auditService = auditService;
        this.eventService = eventService;
    }

    public List<Incident> list(IncidentStatus status) {
        if (status == null) {
            return incidentRepository.findAll().stream()
                    .sorted((a, b) -> b.getStartedAt().compareTo(a.getStartedAt()))
                    .toList();
        }
        return incidentRepository.findByStatusOrderByStartedAtDesc(status);
    }

    public Incident get(Long id) {
        return incidentRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Incident not found: " + id));
    }

    @Transactional
    public Incident transition(Long id, IncidentStatus target) {
        Incident incident = get(id);
        IncidentStatus from = incident.getStatus();
        IncidentStatus next = IncidentStateMachine.transition(from, target);
        incident.setStatus(next);
        if (next == IncidentStatus.RESOLVED) {
            incident.setResolvedAt(Instant.now());
        }
        Incident saved = incidentRepository.save(incident);
        auditService.record(id, "system", "INCIDENT_TRANSITION", from + " -> " + next);
        eventService.publish(id, "INCIDENT_TRANSITION", Map.of("from", from, "to", next));
        return saved;
    }

    @Transactional
    public Incident updateRootCause(Long id, String rootCause, Double confidence) {
        Incident incident = get(id);
        incident.setRootCause(rootCause);
        incident.setConfidence(confidence);
        Incident saved = incidentRepository.save(incident);
        auditService.record(id, "agent", "ROOT_CAUSE_UPDATED", rootCause);
        eventService.publish(id, "ROOT_CAUSE_UPDATED", Map.of("rootCause", rootCause));
        return saved;
    }
}