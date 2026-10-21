package com.aisre.api;

import com.aisre.repo.AgentTaskRepository;
import com.aisre.service.AgentTaskService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 有界批量：/tasks/pending 默认 50、最大 500，避免积压时一次拉回整张任务表。
 */
@ExtendWith(MockitoExtension.class)
class AgentTaskControllerPendingTest {

    @Mock
    private AgentTaskRepository repository;

    @Mock
    private AgentTaskService service;

    private AgentTaskController controller;

    @BeforeEach
    void setUp() {
        controller = new AgentTaskController(repository, service);
    }

    private Pageable capturePageable(int requestedLimit) {
        when(repository.findClaimableQueued(any(Instant.class), any(Pageable.class)))
                .thenReturn(List.of());
        controller.pending(requestedLimit);
        ArgumentCaptor<Pageable> captor = ArgumentCaptor.forClass(Pageable.class);
        verify(repository).findClaimableQueued(any(Instant.class), captor.capture());
        return captor.getValue();
    }

    @Test
    void defaultSizedRequestUsesRequestedLimit() {
        Pageable pageable = capturePageable(50);
        assertEquals(0, pageable.getPageNumber());
        assertEquals(50, pageable.getPageSize());
    }

    @Test
    void limitIsClampedToUpperBound() {
        assertEquals(500, capturePageable(999).getPageSize());
    }

    @Test
    void zeroLimitFallsBackToOne() {
        assertEquals(1, capturePageable(0).getPageSize());
    }

    @Test
    void negativeLimitFallsBackToOne() {
        assertEquals(1, capturePageable(-10).getPageSize());
    }

    @Test
    void pendingCountComesFromDatabaseTruth() {
        when(repository.countClaimableQueued(any(Instant.class))).thenReturn(123L);
        assertEquals(123L, controller.pendingCount().get("count"));
    }
}
