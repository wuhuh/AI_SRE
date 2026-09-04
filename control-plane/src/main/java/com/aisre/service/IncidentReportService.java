package com.aisre.service;

import com.aisre.domain.AgentStep;
import com.aisre.domain.Approval;
import com.aisre.domain.Evidence;
import com.aisre.domain.Incident;
import com.aisre.domain.RemediationAction;
import com.aisre.domain.ToolCall;
import com.aisre.repo.ApprovalRepository;
import com.aisre.repo.IncidentRepository;
import org.springframework.stereotype.Service;

import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@Service
public class IncidentReportService {

    private final IncidentRepository incidentRepository;
    private final IncidentDetailService detailService;
    private final ApprovalRepository approvalRepository;

    public IncidentReportService(IncidentRepository incidentRepository,
                                 IncidentDetailService detailService,
                                 ApprovalRepository approvalRepository) {
        this.incidentRepository = incidentRepository;
        this.detailService = detailService;
        this.approvalRepository = approvalRepository;
    }

    public Map<String, Object> generate(Long incidentId) {
        Incident incident = incidentRepository.findById(incidentId)
                .orElseThrow(() -> new IllegalArgumentException("Incident not found: " + incidentId));
        List<Evidence> evidence = detailService.evidence(incidentId);
        List<ToolCall> toolCalls = detailService.toolCalls(incidentId);
        List<AgentStep> steps = detailService.steps(incidentId);
        List<RemediationAction> remediations = detailService.remediations(incidentId);
        List<Approval> approvals = approvalRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId);

        StringBuilder sb = new StringBuilder();
        sb.append("# Incident Report #").append(incident.getId()).append("\n\n");
        sb.append("- Service: ").append(incident.getService()).append("\n");
        sb.append("- Status: ").append(incident.getStatus()).append("\n");
        sb.append("- Severity: ").append(incident.getSeverity()).append("\n");
        sb.append("- Started At: ").append(format(incident.getStartedAt())).append("\n");
        if (incident.getResolvedAt() != null) {
            sb.append("- Resolved At: ").append(format(incident.getResolvedAt())).append("\n");
        }
        sb.append("- Root Cause: ").append(incident.getRootCause() == null ? "unknown" : incident.getRootCause()).append("\n");
        sb.append("- Confidence: ").append(incident.getConfidence() == null ? "-" : incident.getConfidence()).append("\n\n");

        sb.append("## Agent Steps\n");
        for (AgentStep step : steps) {
            sb.append("- ").append(step.getStepType()).append(": ").append(step.getOutputSummary()).append("\n");
        }
        sb.append("\n## Evidence\n");
        for (Evidence e : evidence) {
            sb.append("- [").append(e.getSource()).append("] ").append(e.getEvidenceKey()).append(" -> ").append(e.getContent()).append("\n");
        }
        sb.append("\n## Tool Calls\n");
        for (ToolCall t : toolCalls) {
            sb.append("- ").append(t.getToolName()).append(" [").append(t.getStatus()).append("] ").append(t.getResultSummary()).append("\n");
        }
        sb.append("\n## Remediations\n");
        for (RemediationAction r : remediations) {
            sb.append("- ").append(r.getToolName()).append(" [").append(r.getStatus()).append("] ").append(r.getResultSummary()).append("\n");
        }
        sb.append("\n## Approvals\n");
        for (Approval a : approvals) {
            sb.append("- ").append(a.getActionType()).append(" [").append(a.getStatus()).append("] by ").append(a.getDecidedBy() == null ? "-" : a.getDecidedBy()).append("\n");
        }

        return Map.of(
                "incidentId", incidentId,
                "report", sb.toString()
        );
    }

    private String format(java.time.Instant instant) {
        return DateTimeFormatter.ISO_INSTANT.format(instant);
    }
}