package com.aisre.service;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.IncidentRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 文档 14.x：Incident 列表必须分页下推 DB，不能在应用层全表扫描。
 * 分页元数据通过 IncidentPage 返回，控制器再用响应头透出。
 */
@ExtendWith(MockitoExtension.class)
class IncidentServicePaginationTest {

    @Mock
    private IncidentRepository repository;

    @Mock
    private AuditService auditService;

    @Mock
    private IncidentEventService eventService;

    private IncidentService service;

    @BeforeEach
    void setUp() {
        service = new IncidentService(repository, auditService, eventService);
    }

    private Page<Incident> page() {
        Incident incident = new Incident("payment-service", "P1", "redis pool", Instant.now());
        incident.setId(1L);
        return new PageImpl<>(List.of(incident), PageRequest.of(2, 25), 120);
    }

    @Test
    void statusFilterUsesPageableAndReturnsTotal() {
        when(repository.findByStatus(eq(IncidentStatus.ROOT_CAUSE_FOUND), any(Pageable.class)))
                .thenReturn(page());

        IncidentService.IncidentPage result = service.list(IncidentStatus.ROOT_CAUSE_FOUND, 2, 25);

        assertEquals(1, result.items().size());
        assertEquals(120, result.total());
        assertEquals(2, result.page());
        assertEquals(25, result.size());

        ArgumentCaptor<Pageable> captor = ArgumentCaptor.forClass(Pageable.class);
        verify(repository).findByStatus(eq(IncidentStatus.ROOT_CAUSE_FOUND), captor.capture());
        Pageable pageable = captor.getValue();
        assertEquals(2, pageable.getPageNumber());
        assertEquals(25, pageable.getPageSize());
        assertNotNull(pageable.getSort().getOrderFor("startedAt"));
        assertEquals(Sort.Direction.DESC,
                pageable.getSort().getOrderFor("startedAt").getDirection());
    }

    @Test
    void noStatusUsesFindAllPageable() {
        when(repository.findAll(any(Pageable.class))).thenReturn(page());

        IncidentService.IncidentPage result = service.list(null, 2, 25);

        assertEquals(120, result.total());
        verify(repository).findAll(any(Pageable.class));
    }
}
