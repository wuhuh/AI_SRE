package com.aisre.service;

import com.aisre.api.dto.ApprovalRequest;
import com.aisre.domain.Approval;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.ApprovalRepository;
import com.aisre.repo.IncidentRepository;
import org.springframework.beans.factory.annotation.Value;
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
    private final long approvalTtlSeconds;

    public ApprovalService(ApprovalRepository approvalRepository,
                           IncidentRepository incidentRepository,
                           AuditService auditService,
                           RemediationExecutor remediationExecutor,
                           @Value("${aisre.approval.ttl-seconds:3600}") long approvalTtlSeconds) {
        this.approvalRepository = approvalRepository;
        this.incidentRepository = incidentRepository;
        this.auditService = auditService;
        this.remediationExecutor = remediationExecutor;
        this.approvalTtlSeconds = approvalTtlSeconds;
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
        // P1-CP-12: PENDING 有期限——过期后 decide 拒绝，不再无限期可执行
        approval.setExpiresAt(Instant.now().plusSeconds(approvalTtlSeconds));
        Approval saved = approvalRepository.save(approval);
        auditService.record(incidentId, requestedBy, "APPROVAL_REQUESTED", actionType);
        return saved;
    }

    @Transactional
    public Approval decide(Long approvalId, ApprovalRequest request) {
        Approval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new IllegalArgumentException("Approval not found: " + approvalId));
        String decision = request.decision().toUpperCase(Locale.ROOT);
        if (!decision.equals("APPROVE") && !decision.equals("REJECT")) {
            throw new IllegalArgumentException("decision must be APPROVE or REJECT");
        }
        // P1-CP-12: 过期审批不再可决定
        if (approval.getExpiresAt() != null && Instant.now().isAfter(approval.getExpiresAt())) {
            throw new IllegalStateException("Approval expired at " + approval.getExpiresAt());
        }
        // P1-CP-12: 终态与 auto-policy 对齐（APPROVED/REJECTED）
        String terminalStatus = decision.equals("APPROVE") ? "APPROVED" : "REJECTED";
        String decidedBy = request.operator() == null || request.operator().isBlank()
                ? "unknown" : request.operator();
        Instant decidedAt = Instant.now();
        String executionToken = decision.equals("APPROVE") ? UUID.randomUUID().toString() : null;

        // P1-CP-06: 条件 UPDATE 消除并发竞态——0 行更新 = 已被并发请求决定 → 409
        int updated = approvalRepository.decideIfPending(
                approvalId, terminalStatus, decidedBy, request.comment(), decidedAt, executionToken);
        if (updated == 0) {
            throw new IllegalStateException("Approval already decided");
        }
        approval.setStatus(terminalStatus);
        approval.setDecidedBy(decidedBy);
        approval.setComment(request.comment());
        approval.setDecidedAt(decidedAt);
        approval.setExecutionToken(executionToken);

        Long incidentId = approval.getIncidentId();
        incidentRepository.findById(incidentId).ifPresent(incident -> {
            if (decision.equals("APPROVE") && incident.getStatus() == IncidentStatus.WAITING_APPROVAL) {
                incident.setStatus(IncidentStatus.REMEDIATING);
                incidentRepository.save(incident);
            }
            // P1-CP-12: REJECT 推进状态回 ROOT_CAUSE_FOUND（操作者可重新诊断/换方案）
            if (decision.equals("REJECT") && incident.getStatus() == IncidentStatus.WAITING_APPROVAL) {
                incident.setStatus(IncidentStatus.ROOT_CAUSE_FOUND);
                incidentRepository.save(incident);
            }
        });
        if (decision.equals("APPROVE")) {
            remediationExecutor.execute(incidentId, approval);
        }
        // P0-07: operator 缺省时不能让审计表 NOT NULL 约束把整个决策事务炸掉
        String operator = request.operator() == null || request.operator().isBlank()
                ? "unknown-operator" : request.operator();
        auditService.record(incidentId, operator, "APPROVAL_DECIDED", terminalStatus);
        return approval;
    }
}
