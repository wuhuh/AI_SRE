package com.aisre.integration;

import com.aisre.service.AgentJobProducer;
import com.aisre.service.NoopAgentJobProducer;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.web.client.ResponseErrorHandler;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * P1-T-02: 核心链路集成测试（真实 Spring 上下文 + Testcontainers）。
 * ingest(Alertmanager webhook) → dedup → incident → diagnosis 回调（agent token）
 * → auto-approval（LOW 风险 auto-policy）→ remediation（MockWebServer 模拟 tool-server）
 * → verification 回调 → RESOLVED；HIGH 风险人工审批决策；AuthInterceptor 矩阵。
 */
@Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class ControlPlaneChainTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("aisre").withUsername("aisre").withPassword("aisre");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    static MockWebServer mockBackends;

    @LocalServerPort
    int port;

    @Autowired
    TestRestTemplate rest;

    @TestConfiguration
    static class TestBeans {
        /** IT 无 RocketMQ namesrv：用 Noop 生产者顶替（链路语义不变）。 */
        @Bean
        @Primary
        AgentJobProducer noopAgentJobProducer() {
            return new NoopAgentJobProducer();
        }
    }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "aisre");
        registry.add("spring.datasource.password", () -> "aisre");
        registry.add("spring.data.redis.host", redis::getHost);
        registry.add("spring.data.redis.port", () -> redis.getMappedPort(6379));
        registry.add("aisre.tool-server.url", () -> mockBackends.url("/").toString());
        registry.add("aisre.agent-runtime.url", () -> mockBackends.url("/").toString());
        registry.add("AISRE_TOOL_SERVER_TOKEN", () -> "it-tool-token");
        registry.add("aisre.agent.token", () -> "it-agent-token");
    }

    @BeforeAll
    static void startMock() {
        mockBackends = new MockWebServer();
        try {
            mockBackends.start();
        } catch (IOException e) {
            throw new IllegalStateException("mock backend failed to start", e);
        }
    }

    @AfterAll
    static void stopMock() throws Exception {
        mockBackends.shutdown();
    }

    @Autowired
    void configureRestTemplate(TestRestTemplate template) {
        // 401/403/5xx 也是被测断言对象 —— RestTemplate 不得对错误码抛异常
        template.getRestTemplate().setErrorHandler(new ResponseErrorHandler() {
            @Override
            public boolean hasError(ClientHttpResponse response) {
                return false;
            }

            @Override
            public void handleError(ClientHttpResponse response) {
            }
        });
    }

    private String base() {
        return "http://127.0.0.1:" + port;
    }

    private static String alertmanagerBody(String service, String alertName) {
        return """
                {"status":"firing","alerts":[{"status":"firing","labels":{"alertname":"%s","service":"%s",\
                "instance":"%s-1","severity":"P1"},"annotations":{"summary":"%s alert for IT"}}]}\
                """.formatted(alertName, service, service, alertName);
    }

    @Test
    @Order(1)
    void fullChainIngestDedupDiagnosisAutoApprovalRemediationVerification() throws Exception {
        // ---- 1. ingest（Alertmanager 契约；AlertController @ResponseStatus(ACCEPTED) → 202）----
        ResponseEntity<String> ingest = post(base() + "/api/v1/alerts/alertmanager",
                alertmanagerBody("payment-service", "HighErrorRate"), null);
        assertTrue(ingest.getStatusCode().is2xxSuccessful(), "ingest should be 2xx: " + ingest.getStatusCode());
        System.out.println("[chain-it] first ingest body=" + ingest.getBody());

        Long incidentId = poll(() -> findIncidentByService("payment-service"),
                id -> id != null, "incident should be created from alertmanager webhook");
        assertNotNull(incidentId);

        // ---- 2. dedup：同 fingerprint 重放不再新建 incident ----
        ResponseEntity<String> replay = post(base() + "/api/v1/alerts/alertmanager",
                alertmanagerBody("payment-service", "HighErrorRate"), null);
        System.out.println("[chain-it] replay ingest http=" + replay.getStatusCode() + " body=" + replay.getBody());
        int incidentCount = poll(() -> {
            JsonNode list = getJson(base() + "/api/v1/incidents");
            return list != null && list.isArray() ? list.size() : -1;
        }, n -> n == 1, "duplicate alert must be deduplicated (still exactly 1 incident)");
        assertEquals(1, incidentCount);

        // ---- 3. diagnosis 回调（agent token；LOW 风险动作 auto-policy 自动批准）----
        mockBackends.enqueue(new MockResponse().setResponseCode(200)
                .setBody("{\"executed\":true,\"detail\":\"docker restart it-pod: mock\"}"));
        mockBackends.enqueue(new MockResponse().setResponseCode(200).setBody("{\"ok\":true}"));

        String diagnosis = """
                {"taskId": 1, "rootCause": "redis_connection_pool_exhausted", "confidence": 0.9,
                 "recommendedActions": ["restart_pod"],
                 "evidence": [{"source": "prometheus", "key": "redis_blocked_clients", "content": "blocked=2"}],
                 "toolCalls": [{"toolName": "redis", "status": "SUCCESS", "argumentsJson": "{}", "resultSummary": "blocked=2", "durationMs": 5}]}
                """;
        assertEquals(200, post(base() + "/api/v1/incidents/" + incidentId + "/diagnosis",
                diagnosis, agentHeaders()).getStatusCode().value());

        // ---- 4. 修复执行 + 链路终态 ----
        poll(() -> {
            JsonNode detail = getJson(base() + "/api/v1/incidents/" + incidentId);
            String status = detail == null ? "" : detail.path("status").asText();
            return ("VERIFYING".equals(status) || "RESOLVED".equals(status)) ? status : null;
        }, s -> s != null, "incident should reach VERIFYING/RESOLVED after successful auto remediation");

        RecordedRequest exec = mockBackends.takeRequest(5, TimeUnit.SECONDS);
        assertNotNull(exec, "tool-server should receive remediation call");
        assertEquals("/api/k8s", exec.getPath());
        assertEquals("it-tool-token", exec.getHeader("X-Execution-Token"));
        assertTrue(exec.getBody().readUtf8().contains("restart_pod"));

        // evidence/toolCalls/steps 落库
        JsonNode evidence = getJson(base() + "/api/v1/incidents/" + incidentId + "/evidence");
        assertTrue(jsonToString(evidence).contains("redis_blocked_clients"), "evidence persisted");
        JsonNode steps = getJson(base() + "/api/v1/incidents/" + incidentId + "/steps");
        assertTrue(jsonToString(steps).contains("DIAGNOSIS"), "agent step persisted");

        // ---- 5. verification 回调 → RESOLVED ----
        assertEquals(200, post(base() + "/api/v1/incidents/" + incidentId + "/verification",
                "{\"status\":\"RECOVERED\",\"detail\":\"5xx back to zero\"}", agentHeaders()).getStatusCode().value());
        poll(() -> {
            JsonNode detail = getJson(base() + "/api/v1/incidents/" + incidentId);
            return "RESOLVED".equals(detail.path("status").asText()) ? "RESOLVED" : null;
        }, s -> s != null, "incident should be RESOLVED after verification callback");
    }

    @Test
    @Order(2)
    void highRiskActionWaitsForHumanApprovalAndAuthMatrixEnforced() throws Exception {
        // 新 incident（不同 fingerprint）
        post(base() + "/api/v1/alerts/alertmanager",
                alertmanagerBody("order-service", "HighLatency"), null);
        Long incidentId = poll(() -> findIncidentByService("order-service"),
                id -> id != null, "second incident should be created for order-service");
        assertNotNull(incidentId);

        // HIGH 风险动作 → WAITING_APPROVAL，无自动执行
        String diagnosis = """
                {"taskId": 2, "rootCause": "capacity_shortage", "confidence": 0.8,
                 "recommendedActions": ["scale_deployment"],
                 "evidence": [{"source": "prometheus", "key": "cpu", "content": "0.95"}]}
                """;
        assertEquals(200, post(base() + "/api/v1/incidents/" + incidentId + "/diagnosis",
                diagnosis, agentHeaders()).getStatusCode().value());
        poll(() -> {
            JsonNode detail = getJson(base() + "/api/v1/incidents/" + incidentId);
            return "WAITING_APPROVAL".equals(detail.path("status").asText()) ? "WAITING_APPROVAL" : null;
        }, s -> s != null, "high risk action must wait for human approval");

        Long approvalId = findPendingApprovalId(incidentId);
        assertNotNull(approvalId, "PENDING approval should exist");

        // ---- AuthInterceptor 矩阵 ----
        String decisionUrl = base() + "/api/v1/approvals/" + approvalId + "/decision";
        // 无 token → 401
        assertEquals(401, post(decisionUrl, "{\"decision\":\"APPROVE\"}", jsonHeaders()).getStatusCode().value());
        // 坏 token → 401
        HttpHeaders bad = jsonHeaders();
        bad.set("Authorization", "Bearer not-a-jwt");
        assertEquals(401, post(decisionUrl, "{\"decision\":\"APPROVE\"}", bad).getStatusCode().value());
        // viewer（低角色）→ 403
        HttpHeaders viewer = jsonHeaders();
        viewer.set("Authorization", "Bearer " + login("viewer", "viewer"));
        assertEquals(403, post(decisionUrl, "{\"decision\":\"APPROVE\",\"operator\":\"viewer-1\"}", viewer).getStatusCode().value());
        // admin → 200（批准触发修复）
        mockBackends.enqueue(new MockResponse().setResponseCode(200)
                .setBody("{\"executed\":true,\"detail\":\"scaled: mock\"}"));
        mockBackends.enqueue(new MockResponse().setResponseCode(200).setBody("{\"ok\":true}"));
        HttpHeaders admin = jsonHeaders();
        admin.set("Authorization", "Bearer " + login("admin", "admin"));
        ResponseEntity<String> decided = post(decisionUrl,
                "{\"decision\":\"APPROVE\",\"operator\":\"it-admin\"}", admin);
        assertEquals(200, decided.getStatusCode().value());
        assertTrue(decided.getBody() != null && decided.getBody().contains("APPROVED"),
                "admin approve should succeed, http=" + decided.getStatusCode() + " body=" + decided.getBody());
        poll(() -> {
            JsonNode detail = getJson(base() + "/api/v1/incidents/" + incidentId);
            String status = detail.path("status").asText();
            return ("VERIFYING".equals(status) || "REMEDIATING".equals(status) || "RESOLVED".equals(status)) ? status : null;
        }, s -> s != null, "approved remediation should drive the incident forward");

        // agent 回调带错 token → 401
        HttpHeaders wrongAgent = jsonHeaders();
        wrongAgent.set("X-Agent-Token", "wrong-token");
        assertEquals(401, post(base() + "/api/v1/incidents/" + incidentId + "/diagnosis",
                "{\"rootCause\":\"x\"}", wrongAgent).getStatusCode().value());
    }

    // ---------- helpers ----------

    private ResponseEntity<String> post(String url, String body, HttpHeaders headers) {
        return rest.exchange(url, HttpMethod.POST, new HttpEntity<>(body, headers == null ? jsonHeaders() : headers), String.class);
    }

    private HttpHeaders agentHeaders() {
        HttpHeaders h = jsonHeaders();
        h.set("X-Agent-Token", "it-agent-token");
        return h;
    }

    private HttpHeaders jsonHeaders() {
        HttpHeaders h = new HttpHeaders();
        h.setContentType(MediaType.APPLICATION_JSON);
        return h;
    }

    private String login(String username, String password) {
        ResponseEntity<Map> resp = rest.postForEntity(base() + "/api/v1/auth/login",
                new HttpEntity<>("{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}", jsonHeaders()), Map.class);
        assertEquals(200, resp.getStatusCode().value(), "login should succeed");
        return String.valueOf(resp.getBody().get("token"));
    }

    private JsonNode getJson(String url) {
        try {
            ResponseEntity<String> resp = rest.getForEntity(url, String.class);
            return resp.getBody() == null ? null : MAPPER.readTree(resp.getBody());
        } catch (Exception e) {
            return null;
        }
    }

    private static String jsonToString(JsonNode node) {
        return node == null ? "" : node.toString();
    }

    private Long findIncidentByService(String service) {
        JsonNode list = getJson(base() + "/api/v1/incidents");
        if (list == null || !list.isArray()) {
            return null;
        }
        for (JsonNode n : list) {
            if (service.equals(n.path("service").asText()) && n.path("id").asLong(0) > 0) {
                return n.path("id").asLong();
            }
        }
        return null;
    }

    private Long findPendingApprovalId(Long incidentId) {
        JsonNode list = getJson(base() + "/api/v1/approvals/incident/" + incidentId);
        if (list == null || !list.isArray()) {
            return null;
        }
        for (JsonNode n : list) {
            if ("PENDING".equals(n.path("status").asText()) && n.path("id").asLong(0) > 0) {
                return n.path("id").asLong();
            }
        }
        return null;
    }

    private static <T> T poll(Supplier<T> probe, java.util.function.Predicate<T> accept, String message) {
        long deadline = System.currentTimeMillis() + 20_000;
        T last = null;
        while (System.currentTimeMillis() < deadline) {
            last = probe.get();
            if (last != null && accept.test(last)) {
                return last;
            }
            try {
                Thread.sleep(400);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        throw new AssertionError("condition not met within 20s: " + message + " (last=" + last + ")");
    }
}
