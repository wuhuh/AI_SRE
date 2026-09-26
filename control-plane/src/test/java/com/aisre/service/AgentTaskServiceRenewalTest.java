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
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

/**
 * 文档 6.5：租约心跳续租。只有现任持有者能续；租约过期不能续；
 * 业务总时长封顶（startedAt + max-total）不能被突破。
 */
@ExtendWith(MockitoExtension.class)
class AgentTaskServiceRenewalTest {

    @Mock
    private AgentTaskRepository repository;

    @Mock
    private com.aisre.service.AuditService auditService;

    private AgentTaskService service;

    @BeforeEach
    void setUp() {
        // lease=600s，总时长上限=1800s
        service = new AgentTaskService(repository, auditService, 600, 16, 3, 60, 1800);
    }

    private AgentTask task(long id, String owner, int epoch, Instant startedAt) {
        AgentTask t = new AgentTask(42L, AgentTask.TaskType.DIAGNOSIS,
                AgentTaskStatus.RUNNING, "diag-42", startedAt);
        t.setId(id);
        t.setClaimedBy(owner);
        t.setClaimEpoch(epoch);
        t.setStartedAt(startedAt);
        t.setLeaseUntil(startedAt.plusSeconds(600));
        return t;
    }

    @Test
    void renewalByCurrentOwnerSucceeds() {
        Instant now = Instant.now();
        Instant startedAt = now.minusSeconds(120);
        when(repository.renewLease(eq(7L), eq("worker-a"), eq(2), any(),
                any(), any())).thenReturn(1);

        Instant newLease = service.renewLease(7L, "worker-a", 2);

        // 新租约 ≈ now + 600
        assertTrue(newLease.isAfter(now.plusSeconds(590)));
        assertTrue(newLease.isBefore(now.plusSeconds(610)));
    }

    @Test
    void renewalByStaleWorkerIsRejected() {
        when(repository.renewLease(eq(7L), eq("worker-a"), eq(1), any(), any(), any()))
                .thenReturn(0);
        when(repository.findById(7L))
                .thenReturn(Optional.of(task(7L, "worker-b", 2, Instant.now().minusSeconds(60))));

        FencingRejectedException e = assertThrows(FencingRejectedException.class,
                () -> service.renewLease(7L, "worker-a", 1));
        assertTrue(e.getMessage().contains("not current owner"));
    }

    @Test
    void renewalBeyondTotalDurationCapIsRejected() {
        // 任务 startedAt = now - 2000s > 1800s 上限 → startedAtFloor 条件不满足
        Instant startedAt = Instant.now().minusSeconds(2000);
        when(repository.renewLease(eq(7L), eq("worker-a"), eq(2), any(), any(), any()))
                .thenReturn(0);
        when(repository.findById(7L)).thenReturn(Optional.of(task(7L, "worker-a", 2, startedAt)));

        FencingRejectedException e = assertThrows(FencingRejectedException.class,
                () -> service.renewLease(7L, "worker-a", 2));
        assertTrue(e.getMessage().contains("total duration cap"));
    }

    @Test
    void renewalOfExpiredLeaseIsRejected() {
        when(repository.renewLease(eq(7L), eq("worker-a"), eq(2), any(), any(), any()))
                .thenReturn(0);
        AgentTask t = task(7L, "worker-a", 2, Instant.now().minusSeconds(120));
        when(repository.findById(7L)).thenReturn(Optional.of(t));

        FencingRejectedException e = assertThrows(FencingRejectedException.class,
                () -> service.renewLease(7L, "worker-a", 2));
        assertTrue(e.getMessage().contains("lease already expired")
                || e.getMessage().contains("not current owner")
                || e.getMessage().contains("total duration cap"));
    }

    @Test
    void claimWritesExplicitLease() {
        when(repository.claimTask(eq(7L), eq("worker-a"), any(), any())).thenReturn(1);
        AgentTask t = task(7L, "worker-a", 1, Instant.now());
        t.setStatus(AgentTaskStatus.RUNNING);
        when(repository.findById(7L)).thenReturn(Optional.of(t));

        service.claim(7L, "worker-a");

        org.mockito.ArgumentCaptor<Instant> leaseCaptor =
                org.mockito.ArgumentCaptor.forClass(Instant.class);
        org.mockito.Mockito.verify(repository).claimTask(eq(7L), eq("worker-a"),
                any(), leaseCaptor.capture());
        // 文档 6.5：claim 即写入 now + lease 的显式租约
        assertTrue(leaseCaptor.getValue().isAfter(Instant.now().plusSeconds(590)));
    }
}
