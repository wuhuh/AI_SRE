package com.aisre.repo;

import com.aisre.domain.Approval;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface ApprovalRepository extends JpaRepository<Approval, Long> {

    List<Approval> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);

    List<Approval> findByIncidentIdAndStatus(Long incidentId, String status);

    /** P1-CP-12: 同 incident+action 复用 PENDING，避免重复审批单。 */
    Optional<Approval> findFirstByIncidentIdAndActionTypeAndStatusOrderByIdDesc(
            Long incidentId, String actionType, String status);

    /**
     * P1-CP-06: 条件 UPDATE 消除 decide 并发竞态（两个请求同时决策同一审批）。
     * 返回 0 行 = 已被别的请求决定，调用方回 409。
     */
    @Modifying
    @Query("""
            UPDATE Approval a
               SET a.status = :status, a.decidedBy = :decidedBy, a.comment = :comment,
                   a.decidedAt = :decidedAt, a.executionToken = :executionToken
             WHERE a.id = :id AND a.status = 'PENDING'
            """)
    int decideIfPending(@Param("id") Long id,
                        @Param("status") String status,
                        @Param("decidedBy") String decidedBy,
                        @Param("comment") String comment,
                        @Param("decidedAt") Instant decidedAt,
                        @Param("executionToken") String executionToken);
}
