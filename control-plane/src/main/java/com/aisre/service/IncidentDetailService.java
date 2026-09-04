package com.aisre.service;

import com.aisre.domain.AgentStep;
import com.aisre.domain.AuditLog;
import com.aisre.domain.Evidence;
import com.aisre.domain.RemediationAction;
import com.aisre.domain.ToolCall;
import com.aisre.repo.AgentStepRepository;
import com.aisre.repo.AuditLogRepository;
import com.aisre.repo.EvidenceRepository;
import com.aisre.repo.RemediationActionRepository;
import com.aisre.repo.ToolCallRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class IncidentDetailService {

    private final EvidenceRepository evidenceRepository;
    private final ToolCallRepository toolCallRepository;
    private final AgentStepRepository agentStepRepository;
    private final RemediationActionRepository remediationActionRepository;
    private final AuditLogRepository auditLogRepository;

    public IncidentDetailService(EvidenceRepository evidenceRepository,
                                 ToolCallRepository toolCallRepository,
                                 AgentStepRepository agentStepRepository,
                                 RemediationActionRepository remediationActionRepository,
                                 AuditLogRepository auditLogRepository) {
        this.evidenceRepository = evidenceRepository;
        this.toolCallRepository = toolCallRepository;
        this.agentStepRepository = agentStepRepository;
        this.remediationActionRepository = remediationActionRepository;
        this.auditLogRepository = auditLogRepository;
    }

    public List<Evidence> evidence(Long incidentId) {
        return evidenceRepository.findByIncidentIdOrderByCollectedAtAsc(incidentId);
    }

    public List<ToolCall> toolCalls(Long incidentId) {
        return toolCallRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId);
    }

    public List<AgentStep> steps(Long incidentId) {
        return agentStepRepository.findByIncidentIdOrderByStepOrderAsc(incidentId);
    }

    public List<RemediationAction> remediations(Long incidentId) {
        return remediationActionRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId);
    }

    public List<AuditLog> auditLogs(Long incidentId) {
        return auditLogRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId);
    }
}