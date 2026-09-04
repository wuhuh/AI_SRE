package com.aisre.service;

import com.aisre.domain.Approval;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.domain.RemediationAction;
import com.aisre.repo.IncidentRepository;
import com.aisre.repo.RemediationActionRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;

@Service
public class RemediationExecutor {

    private final RemediationActionRepository remediationActionRepository;
    private final IncidentRepository incidentRepository;
    private final String toolServerUrl;
    private final String approvalToken;
    private final String agentRuntimeUrl;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    public RemediationExecutor(RemediationActionRepository remediationActionRepository,
                               IncidentRepository incidentRepository,
                               @Value("${aisre.tool-server.url:http://tool-server:8081}") String toolServerUrl,
                               @Value("${aisre.tool-server.approval-token:change-me-in-production}") String approvalToken,
                               @Value("${aisre.agent-runtime.url:http://agent-runtime:8080}") String agentRuntimeUrl) {
        this.remediationActionRepository = remediationActionRepository;
        this.incidentRepository = incidentRepository;
        this.toolServerUrl = toolServerUrl;
        this.approvalToken = approvalToken;
        this.agentRuntimeUrl = agentRuntimeUrl;
    }

    public RemediationAction execute(Long incidentId, Approval approval) {
        String action = approval.getActionType();
        String url = buildUrl(action, approval);
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
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(30))
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            boolean success = response.statusCode() >= 200 && response.statusCode() < 300;
            remediation.setStatus(success ? "SUCCESS" : "FAILED");
            remediation.setResultSummary(response.body().length() > 2000 ? response.body().substring(0, 2000) : response.body());
            remediation.setExecutedAt(Instant.now());
            remediation = remediationActionRepository.save(remediation);

            if (success) {
                Incident incident = incidentRepository.findById(incidentId).orElse(null);
                if (incident != null && IncidentStateMachineSafe.canTransition(incident.getStatus(), IncidentStatus.VERIFYING)) {
                    incident.setStatus(IncidentStatus.VERIFYING);
                    incidentRepository.save(incident);
                    triggerVerification(incident);
                }
            }
        } catch (Exception e) {
            remediation.setStatus("FAILED");
            remediation.setResultSummary("remediation execution failed: " + e.getMessage());
            remediation.setExecutedAt(Instant.now());
            remediation = remediationActionRepository.save(remediation);
        }
        return remediation;
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

    private String buildUrl(String action, Approval approval) {
        String normalized = action == null ? "" : action.trim().toLowerCase();
        String base = toolServerUrl.replaceAll("/+$", "");
        String executionToken = approval.getExecutionToken() != null ? approval.getExecutionToken() : approvalToken;
        String tokenParam = "x-approval-token=" + executionToken;
        return switch (normalized) {
            case "scale_deployment" -> base + "/api/k8s?action=scale_deployment&namespace=default&deployment=default&replicas=3&" + tokenParam;
            case "restart_pod", "restart_service" -> base + "/api/k8s?action=restart_pod&namespace=default&pod=default&" + tokenParam;
            case "delete_pod" -> base + "/api/k8s?action=delete_pod&namespace=default&pod=default&" + tokenParam;
            case "rollback_deployment" -> base + "/api/k8s?action=rollback_deployment&namespace=default&deployment=default&" + tokenParam;
            case "increase_redis_maxclients", "clear_redis_cache" -> base + "/api/redis?command=info";
            case "increase_db_pool_size" -> base + "/api/db?command=health";
            default -> base + "/api/k8s?action=restart_pod&namespace=default&pod=default&" + tokenParam;
        };
    }

    // small helper to avoid direct dependency on state machine class in this context
    private static class IncidentStateMachineSafe {
        static boolean canTransition(IncidentStatus from, IncidentStatus to) {
            return com.aisre.state.IncidentStateMachine.canTransition(from, to);
        }
    }
}