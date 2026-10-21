package com.aisre.service;

import com.aisre.domain.Approval;
import com.aisre.domain.ApprovalStatus;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.domain.RemediationAction;
import com.aisre.repo.IncidentRepository;
import com.aisre.repo.RemediationActionRepository;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.time.Instant;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 文档 11.3：修复成功且 Incident 进入 VERIFYING 后，必须创建持久验证任务；
 * dryRun / 未执行则不能创建，否则会在没修复时触发验证甚至误判恢复。
 */
@ExtendWith(MockitoExtension.class)
class RemediationVerificationTaskTest {

    @Mock
    private RemediationActionRepository remediationRepository;

    @Mock
    private IncidentRepository incidentRepository;

    @Mock
    private AuditService auditService;

    @Mock
    private AgentTaskService agentTaskService;

    private HttpServer server;
    private String responseBody;

    @BeforeEach
    void setUp() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/k8s", exchange -> {
            byte[] body = responseBody.getBytes();
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
    }

    @AfterEach
    void tearDown() {
        server.stop(0);
    }

    private Incident incident() {
        Incident incident = new Incident("payment-service", "P1", "redis pool", Instant.now());
        incident.setId(1L);
        incident.setStatus(IncidentStatus.ROOT_CAUSE_FOUND);
        return incident;
    }

    private RemediationExecutor executor(Incident incident) {
        when(incidentRepository.findById(1L)).thenReturn(Optional.of(incident));
        when(remediationRepository.save(any())).thenAnswer(inv -> {
            RemediationAction action = inv.getArgument(0);
            action.setId(77L);
            return action;
        });
        String url = "http://127.0.0.1:" + server.getAddress().getPort();
        return new RemediationExecutor(remediationRepository, incidentRepository,
                auditService, url, "token", agentTaskService);
    }

    @Test
    void successfulExecutionCreatesVerificationTask() {
        responseBody = "{\"action\":\"restart_pod\",\"executed\":true}";
        Incident incident = incident();
        Approval approval = new Approval(1L, "restart_pod", "{}",
                ApprovalStatus.APPROVED, "tester", Instant.now());

        executor(incident).execute(1L, approval);

        assertEquals(IncidentStatus.VERIFYING, incident.getStatus());
        verify(agentTaskService).createVerificationTask(1L, 77L);
    }

    @Test
    void dryRunDoesNotCreateVerificationTask() {
        responseBody = "{\"action\":\"restart_pod\",\"dryRun\":true}";
        Incident incident = incident();
        Approval approval = new Approval(1L, "restart_pod", "{}",
                ApprovalStatus.APPROVED, "tester", Instant.now());

        executor(incident).execute(1L, approval);

        verify(agentTaskService, never()).createVerificationTask(any(), any());
    }
}
