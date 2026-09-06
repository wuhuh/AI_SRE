package com.aisre.repo;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.List;

public interface IncidentRepository extends JpaRepository<Incident, Long> {

    List<Incident> findByStatusOrderByStartedAtDesc(IncidentStatus status);

    // P1-CP-09: 精确 service 匹配（原 containing 会把 payment-service-v2 聚合进 payment-service）
    List<Incident> findByServiceAndStatusInAndStartedAtAfterOrderByStartedAtDesc(
            String service, List<IncidentStatus> statuses, Instant startedAfter);
}
