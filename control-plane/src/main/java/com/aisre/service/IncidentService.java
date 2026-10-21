package com.aisre.service;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.IncidentRepository;
import com.aisre.state.IncidentStateMachine;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
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

    /**
     * 分页列表：排序下推到 DB，避免应用层全表扫描。
     * page/size 由控制器做边界收敛（page>=0，1<=size<=500）。
     */
    public IncidentPage list(IncidentStatus status, int page, int size) {
        Pageable pageable = PageRequest.of(page, size,
                Sort.by(Sort.Direction.DESC, "startedAt"));
        Page<Incident> result = status == null
                ? incidentRepository.findAll(pageable)
                : incidentRepository.findByStatus(status, pageable);
        return new IncidentPage(result.getContent(), result.getTotalElements(), page, size);
    }

    public record IncidentPage(List<Incident> items, long total, int page, int size) {
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
}