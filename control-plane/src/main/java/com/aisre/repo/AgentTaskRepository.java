package com.aisre.repo;

import com.aisre.domain.AgentTask;
import com.aisre.domain.AgentTaskStatus;
import com.aisre.domain.MqStatus;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
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
    List<AgentTask> findByMqStatusAndMqAttemptsLessThan(MqStatus mqStatus, int maxAttempts);

    /**
     * 文档 11.6：QUEUED 且已过 not_before 的任务才进入领取候选。
     * not_before 为 null 视为立即可领。
     */
    @Query("SELECT t FROM AgentTask t WHERE t.status = com.aisre.domain.AgentTaskStatus.QUEUED "
            + "AND (t.notBefore IS NULL OR t.notBefore <= :now) "
            + "ORDER BY t.createdAt ASC")
    List<AgentTask> findClaimableQueued(@Param("now") Instant now);

    /**
     * 文档 6.7 fencing：锁住任务行用于「校验身份+世代 → 落结果」的原子衔接。
     * 锁在调用方事务提交/回滚时释放——必须是短事务，不得包住外部调用。
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT t FROM AgentTask t WHERE t.id = :id")
    Optional<AgentTask> findByIdForUpdate(@Param("id") Long id);

    /**
     * P1-MQ-02: 原子抢占 —— 仅当任务仍为 QUEUED 时置为 RUNNING。
     * 文档 6.7：同时 claim_epoch + 1，产出本次认领的世代号。
     * 返回受影响行数：0 表示任务已被其他副本抢走。
     */
    @Modifying
    @Query("UPDATE AgentTask t SET t.status = com.aisre.domain.AgentTaskStatus.RUNNING, t.claimedBy = :worker, t.claimedAt = :now, "
            + "t.startedAt = COALESCE(t.startedAt, :now), t.claimEpoch = t.claimEpoch + 1 "
            + "WHERE t.id = :id AND t.status = com.aisre.domain.AgentTaskStatus.QUEUED")
    int claimTask(@Param("id") Long id, @Param("worker") String worker, @Param("now") Instant now);

    /**
     * 文档 6.7 fencing：终态写入必须保留状态前提 + 现任持有者 + 世代校验，
     * 不能只检查 task_id——否则被回收的旧 worker 复活后仍能写终态。
     * 返回受影响行数：0 = 校验失败（任务已易主 / 已终态 / 世代过期）。
     */
    @Modifying
    @Query("UPDATE AgentTask t SET t.status = :target, t.finishedAt = :now, t.error = :error "
            + "WHERE t.id = :id AND t.status = com.aisre.domain.AgentTaskStatus.RUNNING "
            + "AND t.claimedBy = :worker AND t.claimEpoch = :claimEpoch")
    int finishTaskIfOwner(@Param("id") Long id, @Param("worker") String worker,
                          @Param("claimEpoch") int claimEpoch,
                          @Param("target") AgentTaskStatus target,
                          @Param("error") String error, @Param("now") Instant now);

    /**
     * P1-MQ-02: 租约超时回收 —— RUNNING 且 claimedAt 早于 deadline 的任务：
     * 重试次数 +1，未达上限重回 QUEUED；达上限转 DEAD（P1-MQ-03 毒任务，DLQ 等价物）。
     */
    @Modifying
    @Query("UPDATE AgentTask t SET t.attempts = t.attempts + 1, "
            + "t.status = CASE WHEN t.attempts + 1 >= :maxAttempts THEN com.aisre.domain.AgentTaskStatus.DEAD ELSE com.aisre.domain.AgentTaskStatus.QUEUED END, "
            + "t.claimedBy = null, t.claimedAt = null "
            + "WHERE t.status = com.aisre.domain.AgentTaskStatus.RUNNING AND t.claimedAt < :deadline")
    int reclaimExpiredLeases(@Param("deadline") Instant deadline,
                             @Param("maxAttempts") int maxAttempts);

    /** P1-MQ-03: 本次回收转为 DEAD 的毒任务（用于审计/告警）。 */
    List<AgentTask> findByStatusAndAttemptsGreaterThanEqual(AgentTaskStatus status, int minAttempts);
}
