package com.aisre.service;

import com.aisre.api.dto.ApprovalRequest;
import com.aisre.domain.Approval;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.ApprovalRepository;
import com.aisre.repo.IncidentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@Service
public class ApprovalService {

    private final ApprovalRepository approvalRepository;
    private final IncidentRepository incidentRepository;
    private final AuditService auditService;
    private final RemediationExecutor remediationExecutor;

    public ApprovalService(ApprovalRepository approvalRepository,
                           IncidentRepository incidentRepository,
                           AuditService auditService,
                           RemediationExecutor remediationExecutor) {
        this.approvalRepository = approvalRepository;
        this.incidentRepository = incidentRepository;
        this.auditService = auditService;
        this.remediationExecutor = remediationExecutor;
    }

    public List<Approval> listByIncident(Long incidentId) {
        return approvalRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId);
    }

    public Approval create(Long incidentId, String actionType, String actionPayload, String requestedBy) {
        Approval approval = new Approval(
                incidentId,
                actionType,
                actionPayload,
                "PENDING",
                requestedBy,
                Instant.now()
        );
        Approval saved = approvalRepository.save(approval);
        auditService.record(incidentId, requestedBy, "APPROVAL_REQUESTED", actionType);
        return saved;
    }

    @Transactional
    public Approval decide(Long approvalId, ApprovalRequest request) {
        Approval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new IllegalArgumentException("Approval not found: " + approvalId));
        if (!"PENDING".equals(approval.getStatus())) {
            throw new IllegalStateException("Approval already decided");
        }
        String decision = request.decision().toUpperCase(Locale.ROOT);
        if (!decision.equals("APPROVE") && !decision.equals("REJECT")) {
            throw new IllegalArgumentException("decision must be APPROVE or REJECT");
        }
        approval.setStatus(decision);
        approval.setDecidedBy(request.operator() != null ? request.operator() : "unknown");
        approval.setComment(request.comment());
        approval.setDecidedAt(Instant.now());
        if (decision.equals("APPROVE")) {
            approval.setExecutionToken(UUID.randomUUID().toString());
        }
        Approval saved = approvalRepository.save(approval);

        Long incidentId = approval.getIncidentId();
        incidentRepository.findById(incidentId).ifPresent(incident -> {
            if (decision.equals("APPROVE") && incident.getStatus() == IncidentStatus.WAITING_APPROVAL) {
                incident.setStatus(IncidentStatus.REMEDIATING);
                incidentRepository.save(incident);
            }
        });
        if (decision.equals("APPROVE")) {
            remediationExecutor.execute(incidentId, saved);
        }
        // P0-07: operator 缺省时不能让审计表 NOT NULL 约束把整个决策事务炸掉
        String operator = request.operator() == null || request.operator().isBlank()
                ? "unknown-operator" : request.operator();
        auditService.record(incidentId, operator, "APPROVAL_DECIDED", decision);
        return saved;
    }
}