package com.aisre.repo;

import com.aisre.domain.AgentTask;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface AgentTaskRepository extends JpaRepository<AgentTask, Long> {

    List<AgentTask> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);

    Optional<AgentTask> findByIdempotencyKey(String idempotencyKey);

    /** P1-CP-08: 幂等键查询（首键 diag-<incidentId>，重试键 diag-<incidentId>-r<N>）。 */
    Optional<AgentTask> findTopByIdempotencyKeyOrderByIdDesc(String idempotencyKey);

    /** P1-CP-07: outbox 扫描——待投递且未超重试上限的任务。 */
    List<AgentTask> findByMqStatusAndMqAttemptsLessThan(String mqStatus, int maxAttempts);

    List<AgentTask> findByStatusOrderByCreatedAtAsc(String status);

    /**
     * P1-MQ-02: 原子抢占 —— 仅当任务仍为 QUEUED 时置为 RUNNING。
     * 返回受影响行数：0 表示任务已被其他副本抢走。
     */
    @Modifying
    @Query("UPDATE AgentTask t SET t.status = 'RUNNING', t.claimedBy = :worker, t.claimedAt = :now, "
            + "t.startedAt = COALESCE(t.startedAt, :now) "
            + "WHERE t.id = :id AND t.status = 'QUEUED'")
    int claimTask(@Param("id") Long id, @Param("worker") String worker, @Param("now") Instant now);

    /**
     * P1-MQ-02: 租约超时回收 —— RUNNING 且 claimedAt 早于 deadline 的任务：
     * 重试次数 +1，未达上限重回 QUEUED；达上限转 DEAD（P1-MQ-03 毒任务，DLQ 等价物）。
     */
    @Modifying
    @Query("UPDATE AgentTask t SET t.attempts = t.attempts + 1, "
            + "t.status = CASE WHEN t.attempts + 1 >= :maxAttempts THEN 'DEAD' ELSE 'QUEUED' END, "
            + "t.claimedBy = null, t.claimedAt = null "
            + "WHERE t.status = 'RUNNING' AND t.claimedAt < :deadline")
    int reclaimExpiredLeases(@Param("deadline") Instant deadline,
                             @Param("maxAttempts") int maxAttempts);

    /** P1-MQ-03: 本次回收转为 DEAD 的毒任务（用于审计/告警）。 */
    List<AgentTask> findByStatusAndAttemptsGreaterThanEqual(String status, int minAttempts);
}
