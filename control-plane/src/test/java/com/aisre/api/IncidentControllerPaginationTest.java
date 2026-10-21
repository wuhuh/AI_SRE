package com.aisre.api;

import com.aisre.api.dto.IncidentResponse;
import com.aisre.service.AgentResultService;
import com.aisre.service.IncidentDetailService;
import com.aisre.service.IncidentReportService;
import com.aisre.service.IncidentService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.when;

/**
 * 分页边界：page 不能为负；size 收敛到 [1, 500]；
 * 响应体保持数组兼容旧前端，元数据走 X-* 响应头。
 */
@ExtendWith(MockitoExtension.class)
class IncidentControllerPaginationTest {

    @Mock
    private IncidentService incidentService;

    @Mock
    private AgentResultService agentResultService;

    @Mock
    private IncidentDetailService incidentDetailService;

    @Mock
    private IncidentReportService incidentReportService;

    private IncidentController controller;

    @BeforeEach
    void setUp() {
        controller = new IncidentController(incidentService, agentResultService,
                incidentDetailService, incidentReportService);
    }

    @Test
    void negativePageAndZeroSizeAreClamped() {
        when(incidentService.list(isNull(), eq(0), eq(1)))
                .thenReturn(new IncidentService.IncidentPage(List.of(), 0, 0, 1));

        ResponseEntity<List<IncidentResponse>> response = controller.list(null, -5, 0);

        assertEquals(200, response.getStatusCode().value());
        assertNotNull(response.getHeaders().getFirst("X-Total-Count"));
        assertEquals("0", response.getHeaders().getFirst("X-Total-Count"));
        assertEquals("0", response.getHeaders().getFirst("X-Page"));
        assertEquals("1", response.getHeaders().getFirst("X-Page-Size"));
    }

    @Test
    void oversizedPageSizeIsCappedAt500() {
        when(incidentService.list(isNull(), eq(0), eq(500)))
                .thenReturn(new IncidentService.IncidentPage(List.of(), 0, 0, 500));

        ResponseEntity<List<IncidentResponse>> response = controller.list(null, 0, 999);

        assertEquals("500", response.getHeaders().getFirst("X-Page-Size"));
    }
}
