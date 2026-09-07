package com.aisre.repo;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.List;

public interface IncidentRepository extends JpaRepository<Incident, Long> {

    List<Incident> findByStatusOrderByStartedAtDesc(IncidentStatus status);

    /** P2-CP-20: 聚合统计（替代 findAll 全表扫描）。 */
    long countByStatus(IncidentStatus status);

    long countByStatusIn(List<IncidentStatus> statuses);

    /** P2-CP-20: 无过滤列表（替代 findAll + 内存排序）。 */
    List<Incident> findAllByOrderByStartedAtDesc();

    // P1-CP-09: 精确 service 匹配（原 containing 会把 payment-service-v2 聚合进 payment-service）
    List<Incident> findByServiceAndStatusInAndStartedAtAfterOrderByStartedAtDesc(
            String service, List<IncidentStatus> statuses, Instant startedAfter);
}
