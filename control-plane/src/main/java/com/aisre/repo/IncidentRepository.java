package com.aisre.repo;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.Instant;
import java.util.List;

public interface IncidentRepository extends JpaRepository<Incident, Long> {

    List<Incident> findByStatusOrderByStartedAtDesc(IncidentStatus status);

    /** P2-CP-20: 聚合统计（替代 findAll 全表扫描）。 */
    long countByStatus(IncidentStatus status);

    long countByStatusIn(List<IncidentStatus> statuses);

    /** 分页查询：无过滤走 findAll(Pageable)，带状态走 findByStatus(Pageable)。 */
    Page<Incident> findByStatus(IncidentStatus status, Pageable pageable);

    // P1-CP-09: 精确 service 匹配（原 containing 会把 payment-service-v2 聚合进 payment-service）
    List<Incident> findByServiceAndStatusInAndStartedAtAfterOrderByStartedAtDesc(
            String service, List<IncidentStatus> statuses, Instant startedAfter);
}
