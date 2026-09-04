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
        List<Incident> incidents = incidentRepository.findAll();
        long resolved = incidents.stream().filter(i -> i.getStatus() == IncidentStatus.RESOLVED).count();
        long diagnosing = incidents.stream()
                .filter(i -> i.getStatus() == IncidentStatus.DETECTED
                        || i.getStatus() == IncidentStatus.TRIAGING
                        || i.getStatus() == IncidentStatus.DIAGNOSING
                        || i.getStatus() == IncidentStatus.ROOT_CAUSE_FOUND)
                .count();
        long waitingApproval = incidents.stream()
                .filter(i -> i.getStatus() == IncidentStatus.WAITING_APPROVAL)
                .count();
        long failed = incidents.stream().filter(i -> i.getStatus() == IncidentStatus.FAILED).count();

        double avgRecoverySeconds = incidents.stream()
                .filter(i -> i.getResolvedAt() != null && i.getStartedAt() != null)
                .mapToLong(i -> Duration.between(i.getStartedAt(), i.getResolvedAt()).getSeconds())
                .average()
                .orElse(0.0);

        return Map.of(
                "total", incidents.size(),
                "resolved", resolved,
                "diagnosing", diagnosing,
                "waitingApproval", waitingApproval,
                "failed", failed,
                "avgRecoverySeconds", avgRecoverySeconds
        );
    }
}