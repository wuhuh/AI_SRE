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
    private final AgentTaskService agentTaskService;
    private final HttpClient httpClient = HttpClient.newBuilder()
            // 默认 HTTP_2 会对 uvicorn 发 h2c 升级，POST body 被丢弃（422 body null）——锁 1.1
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    public RemediationExecutor(RemediationActionRepository remediationActionRepository,
                               IncidentRepository incidentRepository,
                               AuditService auditService,
                               @Value("${aisre.tool-server.url:http://tool-server:8081}") String toolServerUrl,
                               @Value("${AISRE_TOOL_SERVER_TOKEN:local-dev-token}") String approvalToken,
                               AgentTaskService agentTaskService) {
        this.remediationActionRepository = remediationActionRepository;
        this.incidentRepository = incidentRepository;
        this.auditService = auditService;
        this.toolServerUrl = toolServerUrl;
        this.approvalToken = approvalToken;
        this.agentTaskService = agentTaskService;
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
            // 文档 7.6：execution_id 绑定 remediation 行（持久化后才发请求），
            // 同一行重试复用同一 ID；tool-server 据此对重复请求返回已知结果
            String executionId = "rem-" + remediation.getId();
            Optional<String> body = buildExecutionBody(action, approval, incident, executionId);
            if (body.isEmpty()) {
                remediation.setStatus("FAILED");
                remediation.setResultSummary("refused: unknown action not in fail-closed policy");
                remediation.setExecutedAt(Instant.now());
                remediation = remediationActionRepository.save(remediation);
                log.warn("refused unknown remediation action '{}' for incident {}", action, incidentId);
                auditService.record(incidentId, "remediation-executor", "UNKNOWN_ACTION_REFUSED", action);
                return remediation;
            }
            // 文档 10.4：执行前核对「批准的计划」——重建计划摘要并与审批上绑定的
            // 摘要比对。不一致 = 批准的对象/参数与实际执行的对象/参数不同
            // （教学反例：批准实例 A，执行时名称已复用为实例 B）→ fail-closed 拒绝。
            // planDigest 为 null 的是 V12 之前的旧审批，回退旧行为（不比对）。
            if (approval.getPlanDigest() != null
                    && !approval.getPlanDigest().equals(planDigest(action, body.get()))) {
                remediation.setStatus("FAILED");
                remediation.setResultSummary("refused: execution plan does not match approved plan (digest mismatch)");
                remediation.setExecutedAt(Instant.now());
                remediation = remediationActionRepository.save(remediation);
                log.warn("plan digest mismatch for incident {}: approved={} actual={}",
                        incidentId, approval.getPlanDigest(), planDigest(action, body.get()));
                auditService.record(incidentId, "remediation-executor", "PLAN_DIGEST_MISMATCH",
                        "action=" + action);
                failIncident(incident, "remediation refused: plan does not match approved plan");
                return remediation;
            }
            // tool-server 校验的是共享静态密钥（AISRE_TOOL_SERVER_TOKEN）；
            // 审批上的 per-approval UUID 只用于 CP 侧审计，不能当 tool-server 凭证
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(toolServerUrl.replaceAll("/+$", "") + "/api/k8s"))
                    .timeout(Duration.ofSeconds(30))
                    .header("Content-Type", "application/json")
                    // P0-04: token 走 header，不再拼进 URL（避免进日志/审计泄漏）
                    .header("X-Execution-Token", approvalToken)
                    .POST(HttpRequest.BodyPublishers.ofString(body.get()))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            // 红线 41：2xx 不等于「真的执行了」。tool-server 在没有 docker.sock / 非
            // in-cluster 时返回 200 + {"dryRun": true}——什么都没做。此前只看状态码，
            // 把 dryRun 判成 SUCCESS，进而把 Incident 推到 VERIFYING 并触发验证，
            // k8s 形态下所有修复都是「假成功」：状态机推进、可能判 RECOVERED，而实际未动。
            // 现在解析响应体，显式区分三种结局。注意 FastAPI 序列化不带空格
            // （{"dryRun":true}），所以判定走 JSON 解析而不是字符串匹配。
            boolean dryRun = isDryRun(response.body());
            boolean executed = !dryRun && isExecuted(response.body());
            boolean unknownOutcome = isUnknownOutcome(response.body());
            String outcome;
            if (unknownOutcome) {
                // 文档 7.6/10.10：响应丢失/执行中断的对账态——不能猜成功也不能猜失败
                outcome = "UNKNOWN";
            } else if (dryRun) {
                outcome = "NOT_EXECUTED";
            } else if (executed || (response.statusCode() >= 200 && response.statusCode() < 300)) {
                outcome = "SUCCESS";
            } else {
                outcome = "FAILED";
            }
            log.info("remediation {} for incident {}: HTTP {} outcome={} dryRun={}",
                    action, incidentId, response.statusCode(), outcome, dryRun);
            remediation.setStatus(outcome);
            remediation.setResultSummary(response.body().length() > 2000 ? response.body().substring(0, 2000) : response.body());
            remediation.setExecutedAt(Instant.now());
            remediation = remediationActionRepository.save(remediation);

            if ("SUCCESS".equals(outcome) && incident != null
                    && IncidentStateMachineSafe.canTransition(incident.getStatus(), IncidentStatus.VERIFYING)) {
                incident.setStatus(IncidentStatus.VERIFYING);
                incidentRepository.save(incident);
                // 文档 11.3：验证是持久任务，不再同步等待 Agent 的观察窗。
                // 任务行与 Incident 状态在同一事务提交；Agent 领取后自行等待 + 采 SLI。
                agentTaskService.createVerificationTask(incidentId, remediation.getId());
            } else if ("UNKNOWN".equals(outcome)) {
                // 文档 7.6：UNKNOWN = 无法确认是否执行 → 待对账，不盲目重复。
                // Incident 移出 REMEDIATING 落 FAILED（人工决定是否重发/升级），
                // 审计里带 execution_id 便于对 tool-server 操作记录对账。
                auditService.record(incidentId, "remediation-executor", "REMEDIATION_OUTCOME_UNKNOWN",
                        "executionId=" + remediation.getId() + " action=" + action);
                failIncident(incident, "remediation outcome unknown (needs reconciliation), executionId=rem-"
                        + remediation.getId());
            } else if ("NOT_EXECUTED".equals(outcome)) {
                // 红线 31/41：dryRun 不推进状态、不触发验证。事故回到 ROOT_CAUSE_FOUND
                // 等待人工处置（状态机 REMEDIATING → FAILED 亦可，但「未执行」不是失败，
                // 回 ROOT_CAUSE_FOUND 才允许重新决策/改方案）。
                failIncident(incident, "remediation not executed (dryRun): " + action);
            } else {
                // 红线 31：非 2xx → 此前只标 remediation 行，Incident 永远卡在
                // REMEDIATING（ApprovalService 已先置该状态，且状态机没有「执行失败」自动边）。
                failIncident(incident, "remediation failed: HTTP " + response.statusCode());
            }
        } catch (Exception e) {
            log.warn("remediation {} for incident {} failed: {}", action, incidentId, e.getMessage());
            remediation.setStatus("FAILED");
            remediation.setResultSummary("remediation execution failed: " + e.getMessage());
            remediation.setExecutedAt(Instant.now());
            remediation = remediationActionRepository.save(remediation);
            // 红线 31：异常路径同样必须把 Incident 从 REMEDIATING 里放出来
            failIncident(incident, "remediation exception: " + e.getMessage());
        }
        return remediation;
    }

    /**
     * 红线 31：把卡在 REMEDIATING 的 Incident 推进到终态或可重决策态。
     * 状态机允许 REMEDIATING → FAILED，但「未执行 / 执行失败」更合理的落点是
     * ROOT_CAUSE_FOUND（可重新诊断、换方案、再走审批），只有状态机不允许时才退到 FAILED。
     */
    private void failIncident(Incident incident, String reason) {
        if (incident == null) {
            return;
        }
        IncidentStatus current = incident.getStatus();
        IncidentStatus target = null;
        if (IncidentStateMachineSafe.canTransition(current, IncidentStatus.ROOT_CAUSE_FOUND)) {
            target = IncidentStatus.ROOT_CAUSE_FOUND;
        } else if (IncidentStateMachineSafe.canTransition(current, IncidentStatus.FAILED)) {
            target = IncidentStatus.FAILED;
        }
        if (target == null) {
            log.warn("incident {} stayed in {} — no recovery transition available ({})",
                    incident.getId(), current, reason);
            return;
        }
        incident.setStatus(target);
        incidentRepository.save(incident);
        auditService.record(incident.getId(), "remediation-executor", "REMEDIATION_NOT_COMPLETED",
                current + "->" + target + " " + reason);
        log.info("incident {} moved {} -> {} ({})", incident.getId(), current, target, reason);
    }

    /**
     * 文档 10.4：动作计划摘要 = SHA-256(action + 换行 + 解析后的完整执行 body JSON)。
     * 审批创建时计算并绑定到 Approval.planDigest；执行时按同一规则重建并比对。
     * body 由 LinkedHashMap 按固定顺序构造，序列化稳定。
     */
    static String planDigest(String action, String executionBodyJson) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(((action == null ? "" : action.trim().toLowerCase())
                    + "\n" + executionBodyJson).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(64);
            for (byte b : hash) {
                hex.append(Character.forDigit((b >> 4) & 0xF, 16))
                        .append(Character.forDigit(b & 0xF, 16));
            }
            return hex.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }

    /**
     * 判定 tool-server 响应是否为「未真正执行」的 dryRun 结果。
     * 走 JSON 解析：FastAPI 默认 separators 无空格（{"dryRun":true}），
     * 用字符串匹配 {"dryRun": true} 会漏判 → 又变成假成功。
     */
    static boolean isDryRun(String body) {
        JsonNode node = tryParse(body);
        return node != null && node.path("dryRun").asBoolean(false);
    }

    /** tool-server 明确回报 executed=true（真实执行闭环）。 */
    static boolean isExecuted(String body) {
        JsonNode node = tryParse(body);
        return node != null && node.path("executed").asBoolean(false);
    }

    /**
     * 文档 7.6/10.10：执行结果无法确认（响应丢失后重放命中 IN_FLIGHT 记录等）。
     * 返回 UNKNOWN 的响应带 duplicate=true + status=UNKNOWN。
     */
    static boolean isUnknownOutcome(String body) {
        JsonNode node = tryParse(body);
        return node != null && node.path("duplicate").asBoolean(false)
                && "UNKNOWN".equals(node.path("status").asText(""));
    }

    private static JsonNode tryParse(String body) {
        if (body == null || body.isBlank()) {
            return null;
        }
        try {
            return MAPPER.readTree(body);
        } catch (Exception e) {
            // 非 JSON 响应：交由状态码路径判定，不在这里抛
            return null;
        }
    }

    /**
     * P0-04: 从审批 payload 构造 tool-server 请求 body。
     * payload 缺字段时回退到 incident.service（payload 由 AgentResultService 在
     * 创建审批时写入真实参数）。未知动作返回 empty —— 调用方必须 fail-closed。
     * 文档 7.6：execution_id 随请求下发，tool-server 端按它做操作幂等。
     */
    static Optional<String> buildExecutionBody(String action, Approval approval, Incident incident,
                                               String executionId) {
        String normalized = action == null ? "" : action.trim().toLowerCase();
        JsonNode p = parsePayload(approval == null ? null : approval.getActionPayload());
        String service = incident == null || incident.getService() == null ? "unknown" : incident.getService();
        Map<String, Object> body = new LinkedHashMap<>();
        if (executionId != null && !executionId.isBlank()) {
            body.put("execution_id", executionId);
        }
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

    // small helper to avoid direct dependency on state machine class in this context
    private static class IncidentStateMachineSafe {
        static boolean canTransition(IncidentStatus from, IncidentStatus to) {
            return com.aisre.state.IncidentStateMachine.canTransition(from, to);
        }
    }
}
