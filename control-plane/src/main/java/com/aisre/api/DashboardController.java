package com.aisre.api;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.repo.IncidentRepository;
import com.aisre.service.DashboardService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;
import java.util.List;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardController {

    private final IncidentRepository incidentRepository;
    private final DashboardService dashboardService;

    public DashboardController(IncidentRepository incidentRepository,
                               DashboardService dashboardService) {
        this.incidentRepository = incidentRepository;
        this.dashboardService = dashboardService;
    }

    @GetMapping("/services")
    public List<Map<String, Object>> services() {
        return dashboardService.health();
    }

    @GetMapping("/summary")
    public Map<String, Object> summary() {
        // P2-CP-20: 聚合下推到 DB（count 查询 + 仅恢复时长取已解决行）
        long total = incidentRepository.count();
        long resolved = incidentRepository.countByStatus(IncidentStatus.RESOLVED);
        long diagnosing = incidentRepository.countByStatusIn(List.of(
                IncidentStatus.DETECTED, IncidentStatus.TRIAGING,
                IncidentStatus.DIAGNOSING, IncidentStatus.ROOT_CAUSE_FOUND));
        long waitingApproval = incidentRepository.countByStatus(IncidentStatus.WAITING_APPROVAL);
        long failed = incidentRepository.countByStatus(IncidentStatus.FAILED);

        double avgRecoverySeconds = incidentRepository.findByStatusOrderByStartedAtDesc(IncidentStatus.RESOLVED)
                .stream()
                .filter(i -> i.getResolvedAt() != null && i.getStartedAt() != null)
                .mapToLong(i -> Duration.between(i.getStartedAt(), i.getResolvedAt()).getSeconds())
                .average()
                .orElse(0.0);

        return Map.of(
                "total", total,
                "resolved", resolved,
                "diagnosing", diagnosing,
                "waitingApproval", waitingApproval,
                "failed", failed,
                "avgRecoverySeconds", avgRecoverySeconds
        );
    }
}