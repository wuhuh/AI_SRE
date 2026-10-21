package com.aisre.service;

import com.aisre.domain.AgentTask;
import com.aisre.domain.AgentTaskStatus;
import com.aisre.repo.AgentTaskRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 文档 11.3：恢复验证必须是持久任务，而不是 CP 同步等待 Agent 观察窗。
 * 幂等键绑定 remediation 行，重复回调不能生成第二个验证任务。
 */
@ExtendWith(MockitoExtension.class)
class AgentTaskServiceVerificationTest {

    @Mock
    private AgentTaskRepository repository;

    @Mock
    private AuditService auditService;

    private AgentTaskService service;

    @BeforeEach
    void setUp() {
        service = new AgentTaskService(repository, auditService, 600, 16, 3, 60, 1800);
    }

    @Test
    void createsVerificationTaskBoundToRemediation() {
        when(repository.findByIdempotencyKey("verify-42-7")).thenReturn(Optional.empty());
        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        Optional<AgentTask> created = service.createVerificationTask(42L, 7L);

        assertTrue(created.isPresent());
        AgentTask task = created.get();
        assertEquals(AgentTask.TaskType.VERIFICATION, task.getType());
        assertEquals(AgentTaskStatus.QUEUED, task.getStatus());
        assertEquals("verify-42-7", task.getIdempotencyKey());
        assertEquals(42L, task.getIncidentId());
        verify(auditService).record(eq(42L), eq("system"), eq("VERIFICATION_TASK_CREATED"), eq("verify-42-7"));
    }

    @Test
    void duplicateRemediationDoesNotCreateSecondVerificationTask() {
        AgentTask existing = new AgentTask(42L, AgentTask.TaskType.VERIFICATION,
                AgentTaskStatus.QUEUED, "verify-42-7", Instant.now());
        when(repository.findByIdempotencyKey("verify-42-7")).thenReturn(Optional.of(existing));

        Optional<AgentTask> created = service.createVerificationTask(42L, 7L);

        assertTrue(created.isEmpty());
        verify(repository, never()).save(any());
    }
}
