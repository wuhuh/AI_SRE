package com.aisre.service;

import com.aisre.domain.Approval;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.domain.RemediationAction;
import com.aisre.repo.IncidentRepository;
import com.aisre.repo.RemediationActionRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

@Service
public class RemediationExecutor {

    private static final Logger log = LoggerFactory.getLogger(RemediationExecutor.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final RemediationActionRepository remediationActionRepository;
    private final IncidentRepository incidentRepository;
    private final AuditService auditService;
    private final String toolServerUrl;
    private final String approvalToken;
    private final String agentRuntimeUrl;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    public RemediationExecutor(RemediationActionRepository remediationActionRepository,
                               IncidentRepository incidentRepository,
                               AuditService auditService,
                               @Value("${aisre.tool-server.url:http://tool-server:8081}") String toolServerUrl,
                               @Value("${AISRE_TOOL_SERVER_TOKEN:local-dev-token}") String approvalToken,
                               @Value("${aisre.agent-runtime.url:http://agent-runtime:8080}") String agentRuntimeUrl) {
        this.remediationActionRepository = remediationActionRepository;
        this.incidentRepository = incidentRepository;
        this.auditService = auditService;
        this.toolServerUrl = toolServerUrl;
        this.approvalToken = approvalToken;
        this.agentRuntimeUrl = agentRuntimeUrl;
    }

    public RemediationAction execute(Long incidentId, Approval approval) {
        String action = approval.getActionType();
        Incident incident = incidentRepository.findById(incidentId).orElse(null);
        RemediationAction remediation = new RemediationAction(
                incidentId,
                action,
                approval.getActionPayload() == null ? "{}" : approval.getActionPayload(),
                "EXECUTING",
                approval.getId(),
                "",
                Instant.now()
        );
        remediation = remediationActionRepository.save(remediation);
        try {
            // P0-04: 参数化 body（从审批 payload 构造）；未知动作 fail-closed，不发任何请求
            Optional<String> body = buildExecutionBody(action, approval, incident);
            if (body.isEmpty()) {
                remediation.setStatus("FAILED");
                remediation.setResultSummary("refused: unknown action not in fail-closed policy");
                remediation.setExecutedAt(Instant.now());
                remediation = remediationActionRepository.save(remediation);
                log.warn("refused unknown remediation action '{}' for incident {}", action, incidentId);
                auditService.record(incidentId, "remediation-executor", "UNKNOWN_ACTION_REFUSED", action);
                return remediation;
            }
            String executionToken = approval.getExecutionToken() != null ? approval.getExecutionToken() : approvalToken;
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(toolServerUrl.replaceAll("/+$", "") + "/api/k8s"))
                    .timeout(Duration.ofSeconds(30))
                    .header("Content-Type", "application/json")
                    // P0-04: token 走 header，不再拼进 URL（避免进日志/审计泄漏）
                    .header("X-Execution-Token", executionToken)
                    .POST(HttpRequest.BodyPublishers.ofString(body.get()))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            boolean success = response.statusCode() >= 200 && response.statusCode() < 300;
            log.info("remediation {} for incident {}: HTTP {}", action, incidentId, response.statusCode());
            remediation.setStatus(success ? "SUCCESS" : "FAILED");
            remediation.setResultSummary(response.body().length() > 2000 ? response.body().substring(0, 2000) : response.body());
            remediation.setExecutedAt(Instant.now());
            remediation = remediationActionRepository.save(remediation);

            if (success && incident != null
                    && IncidentStateMachineSafe.canTransition(incident.getStatus(), IncidentStatus.VERIFYING)) {
                incident.setStatus(IncidentStatus.VERIFYING);
                incidentRepository.save(incident);
                triggerVerification(incident);
            }
        } catch (Exception e) {
            log.warn("remediation {} for incident {} failed: {}", action, incidentId, e.getMessage());
            remediation.setStatus("FAILED");
            remediation.setResultSummary("remediation execution failed: " + e.getMessage());
            remediation.setExecutedAt(Instant.now());
            remediation = remediationActionRepository.save(remediation);
        }
        return remediation;
    }

    /**
     * P0-04: 从审批 payload 构造 tool-server 请求 body。
     * payload 缺字段时回退到 incident.service（payload 由 AgentResultService 在
     * 创建审批时写入真实参数）。未知动作返回 empty —— 调用方必须 fail-closed。
     */
    static Optional<String> buildExecutionBody(String action, Approval approval, Incident incident) {
        String normalized = action == null ? "" : action.trim().toLowerCase();
        JsonNode p = parsePayload(approval == null ? null : approval.getActionPayload());
        String service = incident == null || incident.getService() == null ? "unknown" : incident.getService();
        Map<String, Object> body = new LinkedHashMap<>();
        switch (normalized) {
            case "scale_deployment" -> {
                body.put("action", "scale_deployment");
                body.put("namespace", text(p, "namespace", "default"));
                body.put("deployment", text(p, "deployment", service));
                body.put("replicas", intOr(p, "replicas", 3));
            }
            case "restart_pod", "restart_service" -> {
                body.put("action", "restart_pod");
                body.put("namespace", text(p, "namespace", "default"));
                body.put("pod", text(p, "pod", service));
            }
            case "delete_pod" -> {
                body.put("action", "delete_pod");
                body.put("namespace", text(p, "namespace", "default"));
                body.put("pod", text(p, "pod", service));
            }
            case "rollback_deployment" -> {
                body.put("action", "rollback_deployment");
                body.put("namespace", text(p, "namespace", "default"));
                body.put("deployment", text(p, "deployment", service));
            }
            default -> {
                return Optional.empty();
            }
        }
        try {
            return Optional.of(MAPPER.writeValueAsString(body));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    private static JsonNode parsePayload(String payload) {
        try {
            return MAPPER.readTree(payload == null || payload.isBlank() ? "{}" : payload);
        } catch (Exception e) {
            return MAPPER.createObjectNode();
        }
    }

    private static String text(JsonNode node, String field, String fallback) {
        return node != null && node.hasNonNull(field) && !node.get(field).asText().isBlank()
                ? node.get(field).asText() : fallback;
    }

    private static int intOr(JsonNode node, String field, int fallback) {
        return node != null && node.has(field) && node.get(field).isInt() ? node.get(field).asInt() : fallback;
    }

    private void triggerVerification(Incident incident) {
        try {
            String summary = incident.getSummary() == null ? "" : incident.getSummary().replace("\"", "\\\"");
            String body = """
                    {"incident_id": %d, "alert": {"service": "%s", "severity": "%s", "summary": "%s"}}
                    """.formatted(incident.getId(), incident.getService(), incident.getSeverity(), summary);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(agentRuntimeUrl.replaceAll("/+$", "") + "/api/v1/agent/verify"))
                    .timeout(Duration.ofSeconds(30))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (Exception e) {
            // Verification is best-effort; the incident remains in VERIFYING for manual retry.
        }
    }

    // small helper to avoid direct dependency on state machine class in this context
    private static class IncidentStateMachineSafe {
        static boolean canTransition(IncidentStatus from, IncidentStatus to) {
            return com.aisre.state.IncidentStateMachine.canTransition(from, to);
        }
    }
}
