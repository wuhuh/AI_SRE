package com.aisre.service;

import com.aisre.api.dto.DiagnosisRequest;
import com.aisre.api.dto.EvidenceDTO;
import com.aisre.api.dto.RemediationRequest;
import com.aisre.api.dto.ToolCallDTO;
import com.aisre.api.dto.VerificationRequest;
import com.aisre.domain.AgentStep;
import com.aisre.domain.Approval;
import com.aisre.domain.ApprovalStatus;
import com.aisre.domain.Evidence;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.domain.RemediationAction;
import com.aisre.domain.ToolCall;
import com.aisre.repo.AgentStepRepository;
import com.aisre.repo.ApprovalRepository;
import com.aisre.repo.EvidenceRepository;
import com.aisre.repo.IncidentRepository;
import com.aisre.repo.RemediationActionRepository;
import com.aisre.repo.ToolCallRepository;
import com.aisre.security.RiskPolicy;
import com.aisre.state.IncidentStateMachine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class AgentResultService {

    private static final Logger log = LoggerFactory.getLogger(AgentResultService.class);

    private final IncidentRepository incidentRepository;
    private final EvidenceRepository evidenceRepository;
    private final ToolCallRepository toolCallRepository;
    private final AgentStepRepository agentStepRepository;
    private final RemediationActionRepository remediationActionRepository;
    private final AuditService auditService;
    private final IncidentEventService eventService;
    private final ApprovalRepository approvalRepository;
    private final RemediationExecutor remediationExecutor;
    private final TransactionTemplate requiresNewTx;

    public AgentResultService(IncidentRepository incidentRepository,
                              EvidenceRepository evidenceRepository,
                              ToolCallRepository toolCallRepository,
                              AgentStepRepository agentStepRepository,
                              RemediationActionRepository remediationActionRepository,
                              AuditService auditService,
                              IncidentEventService eventService,
                              ApprovalRepository approvalRepository,
                              RemediationExecutor remediationExecutor,
                              PlatformTransactionManager transactionManager) {
        this.requiresNewTx = new TransactionTemplate(transactionManager);
        this.requiresNewTx.setPropagationBehavior(TransactionTemplate.PROPAGATION_REQUIRES_NEW);
        this.incidentRepository = incidentRepository;
        this.evidenceRepository = evidenceRepository;
        this.toolCallRepository = toolCallRepository;
        this.agentStepRepository = agentStepRepository;
        this.remediationActionRepository = remediationActionRepository;
        this.auditService = auditService;
        this.eventService = eventService;
        this.approvalRepository = approvalRepository;
        this.remediationExecutor = remediationExecutor;
    }

    @Transactional
    public Incident saveDiagnosis(Long incidentId, DiagnosisRequest request) {
        Incident incident = getIncident(incidentId);
        // P0-05: 幂等 —— 诊断结果只允许写入一次（DIAGNOSING → ROOT_CAUSE_FOUND）。
        // 重复回调（网络重试/多副本竞态/重放）直接返回现状，不再追加重复证据与审计。
        if (incident.getStatus().ordinal() >= IncidentStatus.ROOT_CAUSE_FOUND.ordinal()) {
            log.info("diagnosis callback ignored (incident {} already {}, idempotent replay)", incidentId, incident.getStatus());
            return incident;
        }
        if (incident.getStatus() == IncidentStatus.DETECTED || incident.getStatus() == IncidentStatus.TRIAGING) {
            incident.setStatus(IncidentStatus.DIAGNOSING);
        }
        transitionIfAllowed(incident, IncidentStatus.ROOT_CAUSE_FOUND);
        incident.setRootCause(request.rootCause());
        incident.setConfidence(request.confidence());
        if (request.recommendedActions() != null) {
            incident.setRecommendedActions(String.join(", ", request.recommendedActions()));
        }
        incidentRepository.save(incident);

        if (request.evidence() != null) {
            for (EvidenceDTO dto : request.evidence()) {
                evidenceRepository.save(new Evidence(
                        incidentId,
                        request.taskId(), // P2-CP-23: 链路关联（此前断链 null）
                        dto.source(),
                        dto.key(),
                        dto.content(),
                        dto.query(),
                        dto.timeRange(),
                        dto.timestamp() != null ? dto.timestamp() : Instant.now() // P2-AR-09
                ));
            }
        }

        if (request.toolCalls() != null) {
            for (ToolCallDTO dto : request.toolCalls()) {
                toolCallRepository.save(new ToolCall(
                        incidentId,
                        request.taskId(), // P2-CP-23: 链路关联（此前断链 null）
                        dto.toolName(),
                        // P2-CP-23: 风险来源=agent 端 ToolSpec（策略工件），缺省 READ_ONLY
                        dto.riskLevel() != null ? dto.riskLevel() : "READ_ONLY",
                        dto.status() != null ? dto.status() : "SUCCESS",
                        dto.argumentsJson() != null ? dto.argumentsJson() : "{}",
                        dto.resultSummary(),
                        dto.durationMs(),
                        dto.error(),
                        dto.createdAt() != null ? dto.createdAt() : Instant.now()
                ));
            }
        }

        agentStepRepository.save(new AgentStep(
                request.taskId() == null ? 0L : request.taskId(),
                incidentId,
                1,
                "DIAGNOSIS",
                "SUCCESS",
                "Agent diagnosis completed",
                request.rootCause(),
                Instant.now()
        ));

        boolean hasHighRisk = false;
        if (request.recommendedActions() != null) {
            for (String action : request.recommendedActions()) {
                // P0-04: 审批携带真实参数（服务名驱动），不再写死 "{}"/"default"
                String payload = buildActionPayload(action, incident.getService());
                if (RiskPolicy.requiresApproval(action)) {
                    hasHighRisk = true;
                    // P1-CP-12: 同 incident+action 已有 PENDING 则复用，不重复建审批单
                    if (approvalRepository
                            .findFirstByIncidentIdAndActionTypeAndStatusOrderByIdDesc(
                                    incidentId, action, ApprovalStatus.PENDING).isEmpty()) {
                        approvalRepository.save(new Approval(
                                incidentId,
                                action,
                                payload,
                                ApprovalStatus.PENDING,
                                "agent",
                                Instant.now()
                        ));
                    }
                } else {
                    Approval autoApproval = new Approval(
                            incidentId,
                            action,
                            payload,
                            ApprovalStatus.APPROVED,
                            "auto-policy",
                            Instant.now()
                    );
                    autoApproval.setDecidedBy("auto-policy");
                    autoApproval.setDecidedAt(Instant.now());
                    final Approval savedAuto = approvalRepository.save(autoApproval);
                    // P1-CP-11: 修复执行（HTTP 外呼）移出事务——提交后再执行，
                    // 不让 tool-server 的网络延迟拖长 DB 事务/持锁
                    runAfterCommit(() -> remediationExecutor.execute(incidentId, savedAuto));
                }
            }
        }
        if (hasHighRisk) {
            transitionIfAllowed(incident, IncidentStatus.WAITING_APPROVAL);
        }

        log.info("diagnosis saved: incidentId={}, rootCause={}, taskId={}", incidentId, request.rootCause(), request.taskId());
        auditService.record(incidentId, "agent", "DIAGNOSIS_SAVED", request.rootCause());
        eventService.publish(incidentId, "DIAGNOSIS_SAVED", Map.of("rootCause", request.rootCause()));
        return incident;
    }

    @Transactional
    public Incident saveVerification(Long incidentId, VerificationRequest request) {
        Incident incident = getIncident(incidentId);
        if (incident.getStatus() == IncidentStatus.DETECTED || incident.getStatus() == IncidentStatus.TRIAGING) {
            incident.setStatus(IncidentStatus.DIAGNOSING);
        }
        if (incident.getStatus() == IncidentStatus.DIAGNOSING) {
            incident.setStatus(IncidentStatus.ROOT_CAUSE_FOUND);
        }
        transitionIfAllowed(incident, IncidentStatus.VERIFYING);

        if (request.evidence() != null) {
            for (EvidenceDTO dto : request.evidence()) {
                evidenceRepository.save(new Evidence(
                        incidentId,
                        request.taskId(), // P2-CP-23: 链路关联（此前断链 null）
                        dto.source(),
                        dto.key(),
                        dto.content(),
                        dto.query(),
                        dto.timeRange(),
                        dto.timestamp() != null ? dto.timestamp() : Instant.now() // P2-AR-09
                ));
            }
        }

        IncidentStatus resultStatus;
        String status = request.status() == null ? "UNKNOWN" : request.status().toUpperCase(Locale.ROOT);
        switch (status) {
            case "RECOVERED" -> resultStatus = IncidentStatus.RESOLVED;
            case "NOT_RECOVERED" -> resultStatus = IncidentStatus.DIAGNOSING;
            default -> resultStatus = IncidentStatus.FAILED;
        }
        transitionIfAllowed(incident, resultStatus);
        incidentRepository.save(incident);

        agentStepRepository.save(new AgentStep(
                0L,
                incidentId,
                2,
                "VERIFICATION",
                status,
                "Verification result: " + status,
                request.detail(),
                Instant.now()
        ));
        auditService.record(incidentId, "agent", "VERIFICATION_SAVED", status);
        eventService.publish(incidentId, "VERIFICATION_SAVED", Map.of("status", status));
        return incident;
    }

    @Transactional
    public RemediationAction createRemediation(Long incidentId, RemediationRequest request) {
        RemediationAction action = new RemediationAction(
                incidentId,
                request.toolName(),
                request.argumentsJson() != null ? request.argumentsJson() : "{}",
                request.status() != null ? request.status() : "PENDING",
                request.approvalId(),
                request.resultSummary() != null ? request.resultSummary() : "",
                Instant.now()
        );
        RemediationAction saved = remediationActionRepository.save(action);
        auditService.record(incidentId, "agent", "REMEDIATION_CREATED", request.toolName());
        eventService.publish(incidentId, "REMEDIATION_CREATED", Map.of("toolName", request.toolName()));
        return saved;
    }

    private Incident getIncident(Long incidentId) {
        return incidentRepository.findById(incidentId)
                .orElseThrow(() -> new IllegalArgumentException("Incident not found: " + incidentId));
    }

    /**
     * P0-04: 审批创建时写入真实执行参数（与 RemediationExecutor.buildExecutionBody
     * 的字段约定一致）。未知/无参数动作写 "{}"，执行端 fail-closed 拒绝。
     */
    private String buildActionPayload(String action, String service) {
        String target = service == null || service.isBlank() ? "unknown" : service;
        Map<String, Object> payload = new java.util.LinkedHashMap<>();
        String normalized = action == null ? "" : action.trim().toLowerCase();
        switch (normalized) {
            case "scale_deployment" -> {
                payload.put("namespace", "default");
                payload.put("deployment", target);
                payload.put("replicas", 3);
            }
            case "restart_pod", "restart_service", "delete_pod" -> {
                payload.put("namespace", "default");
                payload.put("pod", target);
            }
            case "rollback_deployment" -> {
                payload.put("namespace", "default");
                payload.put("deployment", target);
            }
            default -> {
                return "{}";
            }
        }
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(payload);
        } catch (Exception e) {
            return "{}";
        }
    }

    private void transitionIfAllowed(Incident incident, IncidentStatus target) {
        // P1-CP-10: 同状态视为幂等重放（回调重试），放行不抛；其余非法流转抛 409
        // （原静默忽略会掩盖真实的状态机破坏）
        if (incident.getStatus() == target) {
            return;
        }
        if (!IncidentStateMachine.canTransition(incident.getStatus(), target)) {
            throw new IllegalStateException(
                    "Invalid incident transition: " + incident.getStatus() + " -> " + target);
        }
        incident.setStatus(target);
    }

    /**
     * P1-CP-11: 事务提交后执行副作用（HTTP 外呼/修复落行）。
     * 关键：afterCommit 里不能再往"已提交的死事务"上写（REQUIRED 会静默丢失），
     * 必须用 REQUIRES_NEW 开新事务；无事务时直接执行。
     */
    private void runAfterCommit(Runnable action) {
        if (org.springframework.transaction.support.TransactionSynchronizationManager.isSynchronizationActive()) {
            org.springframework.transaction.support.TransactionSynchronizationManager
                    .registerSynchronization(new org.springframework.transaction.support.TransactionSynchronization() {
                        @Override
                        public void afterCommit() {
                            requiresNewTx.executeWithoutResult(status -> action.run());
                        }
                    });
        } else {
            action.run();
        }
    }
}