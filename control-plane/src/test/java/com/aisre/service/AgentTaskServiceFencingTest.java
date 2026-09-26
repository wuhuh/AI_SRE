package com.aisre.service;

import com.aisre.domain.AgentTask;
import com.aisre.domain.AgentTaskStatus;
import com.aisre.repo.AgentTaskRepository;
import com.aisre.service.AgentTaskService.FencingRejectedException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 文档 6.7 fencing：终态写入必须同时校验 status=RUNNING + claimedBy + claimEpoch。
 * 旧 worker（被租约回收后复活）的 complete/fail 必须被拒绝（0 行更新 → FencingRejectedException）。
 */
@ExtendWith(MockitoExtension.class)
class AgentTaskServiceFencingTest {

    @Mock
    private AgentTaskRepository repository;

    @Mock
    private com.aisre.service.AuditService auditService;

    private AgentTaskService service;

    @BeforeEach
    void setUp() {
        service = new AgentTaskService(repository, auditService, 600, 16);
    }

    private AgentTask task(long id, String owner, int epoch, AgentTaskStatus status) {
        AgentTask task = new AgentTask(42L, AgentTask.TaskType.DIAGNOSIS, status, "diag-42", Instant.now());
        task.setId(id);
        task.setClaimedBy(owner);
        task.setClaimEpoch(epoch);
        return task;
    }

    @Test
    void completeByCurrentOwnerSucceeds() {
        when(repository.finishTaskIfOwner(eq(7L), eq("worker-a"), eq(2),
                eq(AgentTaskStatus.COMPLETED), isNull(), any()))
                .thenReturn(1);
        when(repository.findById(7L))
                .thenReturn(Optional.of(task(7L, "worker-a", 2, AgentTaskStatus.COMPLETED)));

        AgentTask result = service.complete(7L, "worker-a", 2);

        assertEquals(AgentTaskStatus.COMPLETED, result.getStatus());
    }

    @Test
    void completeByStaleWorkerIsRejected() {
        // 旧 worker（epoch 1）复活后写入：任务已是 epoch 2 → 0 行更新 → 拒绝
        when(repository.finishTaskIfOwner(eq(7L), eq("worker-a"), eq(1),
                eq(AgentTaskStatus.COMPLETED), isNull(), any()))
                .thenReturn(0);

        assertThrows(FencingRejectedException.class,
                () -> service.complete(7L, "worker-a", 1));
    }

    @Test
    void completeAfterReassignmentIsRejected() {
        // 任务被回收后被 worker-b 认领；worker-a 仍持旧凭据
        when(repository.finishTaskIfOwner(eq(7L), eq("worker-a"), eq(1),
                eq(AgentTaskStatus.COMPLETED), isNull(), any()))
                .thenReturn(0);

        assertThrows(FencingRejectedException.class,
                () -> service.complete(7L, "worker-a", 1));
    }

    @Test
    void failByStaleWorkerIsRejected() {
        when(repository.finishTaskIfOwner(eq(7L), eq("worker-a"), eq(1),
                eq(AgentTaskStatus.FAILED), anyString(), any()))
                .thenReturn(0);

        assertThrows(FencingRejectedException.class,
                () -> service.fail(7L, "worker-a", 1, "boom"));
    }

    @Test
    void claimReturnsTaskWithNewEpoch() {
        when(repository.claimTask(eq(7L), eq("worker-a"), any())).thenReturn(1);
        when(repository.findById(7L))
                .thenReturn(Optional.of(task(7L, "worker-a", 3, AgentTaskStatus.RUNNING)));

        Optional<AgentTask> claimed = service.claim(7L, "worker-a");

        assertEquals(3, claimed.orElseThrow().getClaimEpoch());
        verify(repository).claimTask(eq(7L), eq("worker-a"), any());
    }
}
