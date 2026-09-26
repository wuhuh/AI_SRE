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
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 文档 11.6：重诊环闭合。NOT_RECOVERED 后必须真正创建下一轮诊断任务，
 * 且满足：轮次幂等键 diag-&lt;id&gt;-r&lt;N&gt;、not_before 退避、轮次上限、
 * 重复 verification 回调不重复生成下一轮。
 */
@ExtendWith(MockitoExtension.class)
class AgentTaskServiceRediagnosisTest {

    @Mock
    private AgentTaskRepository repository;

    @Mock
    private com.aisre.service.AuditService auditService;

    private AgentTaskService service;

    @BeforeEach
    void setUp() {
        service = new AgentTaskService(repository, auditService, 600, 16, 3, 60, 1800);
    }

    private AgentTask task(String key) {
        AgentTask t = new AgentTask(42L, AgentTask.TaskType.DIAGNOSIS,
                AgentTaskStatus.QUEUED, key, Instant.now());
        t.setId(1L);
        return t;
    }

    @Test
    void createsRound2AfterFirstTaskCompleted() {
        when(repository.findByIncidentIdOrderByCreatedAtAsc(42L))
                .thenReturn(List.of(task("diag-42")));
        when(repository.findByIdempotencyKey("diag-42-r2")).thenReturn(Optional.empty());
        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        Optional<AgentTask> created = service.createRediagnosisTask(42L);

        assertTrue(created.isPresent());
        assertEquals("diag-42-r2", created.get().getIdempotencyKey());
        // 文档 11.6：新任务必须有 not_before 退避
        assertTrue(created.get().getNotBefore().isAfter(Instant.now()));
        verify(auditService).record(eq(42L), eq("system"), eq("REDIAGNOSIS_TASK_CREATED"), any());
    }

    @Test
    void computesRoundFromHighestExistingKey() {
        when(repository.findByIncidentIdOrderByCreatedAtAsc(42L))
                .thenReturn(List.of(task("diag-42"), task("diag-42-r2")));
        when(repository.findByIdempotencyKey("diag-42-r3")).thenReturn(Optional.empty());
        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        Optional<AgentTask> created = service.createRediagnosisTask(42L);

        assertEquals("diag-42-r3", created.orElseThrow().getIdempotencyKey());
    }

    @Test
    void duplicateCallbackWithSameRoundKeyDoesNotCreateAnotherTask() {
        // 上一轮回调已创建 diag-42-r2 且仍存在（尚未被消费完成）；
        // 重放/重复回调再次到达 → 同键已存在 → 不再落库（键级幂等）。
        // 注：跨「已推进轮次」的重放由 saveVerification 的 diagnosisRound 守卫负责。
        when(repository.findByIncidentIdOrderByCreatedAtAsc(42L))
                .thenReturn(List.of(task("diag-42")));
        when(repository.findByIdempotencyKey("diag-42-r2")).thenReturn(Optional.of(task("diag-42-r2")));

        Optional<AgentTask> created = service.createRediagnosisTask(42L);

        assertTrue(created.isEmpty());
        verify(repository, never()).save(any());
    }

    @Test
    void stopsAtRoundCapAndEscalates() {
        when(repository.findByIncidentIdOrderByCreatedAtAsc(42L))
                .thenReturn(List.of(task("diag-42"), task("diag-42-r2"), task("diag-42-r3")));

        Optional<AgentTask> created = service.createRediagnosisTask(42L);

        assertTrue(created.isEmpty());
        verify(auditService).record(org.mockito.ArgumentMatchers.eq(42L),
                org.mockito.ArgumentMatchers.eq("system"),
                org.mockito.ArgumentMatchers.eq("REDIAGNOSIS_ESCALATED"),
                org.mockito.ArgumentMatchers.any());
        verify(repository, never()).save(any());
    }
}
