package com.aisre.service;

import com.aisre.domain.AgentTask;
import com.aisre.domain.AgentTaskStatus;
import com.aisre.repo.AgentTaskRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Optional;

/**
 * P1-MQ-02: 任务领取与生命周期。
 * - claim：条件 UPDATE 原子抢占（QUEUED → RUNNING），抢不到返回空；
 * - complete / fail：RUNNING → 终态；
 * - 定时回收：RUNNING 且租约超时的任务重回 QUEUED（worker 崩溃自愈）。
 */
@Service
public class AgentTaskService {

    private static final Logger log = LoggerFactory.getLogger(AgentTaskService.class);

    private final AgentTaskRepository agentTaskRepository;
    private final com.aisre.service.AuditService auditService;
    private final long leaseSeconds;
    private final int maxAttempts;
    private final int maxRediagnosisRounds;
    private final long rediagnosisBackoffSeconds;
    private final long maxTaskDurationSeconds;

    public AgentTaskService(AgentTaskRepository agentTaskRepository,
                            com.aisre.service.AuditService auditService,
                            @Value("${aisre.task.lease-seconds:600}") long leaseSeconds,
                            @Value("${aisre.task.max-attempts:16}") int maxAttempts,
                            @Value("${aisre.rediagnosis.max-rounds:3}") int maxRediagnosisRounds,
                            @Value("${aisre.rediagnosis.backoff-seconds:60}") long rediagnosisBackoffSeconds,
                            @Value("${aisre.task.max-total-seconds:1800}") long maxTaskDurationSeconds) {
        this.agentTaskRepository = agentTaskRepository;
        this.auditService = auditService;
        this.leaseSeconds = leaseSeconds;
        this.maxAttempts = maxAttempts;
        this.maxRediagnosisRounds = maxRediagnosisRounds;
        this.rediagnosisBackoffSeconds = rediagnosisBackoffSeconds;
        this.maxTaskDurationSeconds = maxTaskDurationSeconds;
    }

    @Transactional
    public Optional<AgentTask> claim(Long taskId, String worker) {
        Instant now = Instant.now();
        // 文档 6.5：claim 即写入显式租约；心跳续租在此基础上延长（受总时长封顶）
        int claimed = agentTaskRepository.claimTask(taskId, worker, now,
                now.plusSeconds(leaseSeconds));
        if (claimed == 0) {
            log.debug("task {} claim missed by {} (already claimed)", taskId, worker);
            return Optional.empty();
        }
        log.info("task {} claimed by {} (epoch {})", taskId, worker,
                agentTaskRepository.findById(taskId).map(AgentTask::getClaimEpoch).orElse(-1));
        return agentTaskRepository.findById(taskId);
    }

    /**
     * 文档 6.5：租约心跳续租。只能由现任持有者发起（worker + claim_epoch，
     * 与 fencing 同一条校验线）；且不能无限延长业务总 deadline——
     * 新租约不得越过 startedAt + max-total-seconds。
     * 续租失败抛 FencingRejectedException：任务已易主 / 租约已过期（将被回收）/ 超总上限。
     */
    @Transactional
    public Instant renewLease(Long taskId, String worker, int claimEpoch) {
        Instant now = Instant.now();
        Instant newLeaseUntil = now.plusSeconds(leaseSeconds);
        // startedAtFloor：允许续租的最晚开始时间。startedAt 早于它 = 任务总时长
        // 已越过上限，续租会突破业务 deadline → 拒绝。
        Instant startedAtFloor = newLeaseUntil.minusSeconds(maxTaskDurationSeconds);
        int updated = agentTaskRepository.renewLease(
                taskId, worker, claimEpoch, now, newLeaseUntil, startedAtFloor);
        if (updated == 0) {
            AgentTask task = agentTaskRepository.findById(taskId).orElse(null);
            String reason;
            if (task == null) {
                reason = "not found";
            } else if (task.getStatus() != AgentTaskStatus.RUNNING) {
                reason = "status=" + task.getStatus();
            } else if (!worker.equals(task.getClaimedBy()) || claimEpoch != task.getClaimEpoch()) {
                reason = "not current owner (owner=" + task.getClaimedBy()
                        + ", epoch=" + task.getClaimEpoch() + ")";
            } else if (task.getStartedAt() != null
                    && !task.getStartedAt().isAfter(startedAtFloor)) {
                reason = "total duration cap reached (startedAt=" + task.getStartedAt()
                        + ", max=" + maxTaskDurationSeconds + "s)";
            } else {
                reason = "lease already expired";
            }
            throw new FencingRejectedException(
                    "lease renewal refused for task %s (worker=%s epoch=%d): %s"
                            .formatted(taskId, worker, claimEpoch, reason));
        }
        log.debug("task {} lease renewed by {} (epoch {}) until {}", taskId, worker, claimEpoch, newLeaseUntil);
        return newLeaseUntil;
    }

    /**
     * 文档 6.7 fencing：终态写入校验现任持有者 + 世代。
     * 校验失败（任务已易主 / 已终态 / 旧世代）抛 FencingRejectedException，
     * 调用方（Agent）收到 409——旧结果不允许落库。
     */
    @Transactional
    public AgentTask complete(Long taskId, String worker, int claimEpoch) {
        int updated = agentTaskRepository.finishTaskIfOwner(
                taskId, worker, claimEpoch, AgentTaskStatus.COMPLETED, null, Instant.now());
        if (updated == 0) {
            throw new FencingRejectedException(
                    "task %s not owned by worker '%s' at epoch %d (already reassigned or finished)"
                            .formatted(taskId, worker, claimEpoch));
        }
        log.info("task {} completed by {} (epoch {})", taskId, worker, claimEpoch);
        return getTask(taskId);
    }

    /** 文档 6.7 fencing：fail 与 complete 走同一条现任持有者校验。 */
    @Transactional
    public AgentTask fail(Long taskId, String worker, int claimEpoch, String error) {
        String truncated = error == null ? "unknown error"
                : error.substring(0, Math.min(error.length(), 4000));
        int updated = agentTaskRepository.finishTaskIfOwner(
                taskId, worker, claimEpoch, AgentTaskStatus.FAILED, truncated, Instant.now());
        if (updated == 0) {
            throw new FencingRejectedException(
                    "task %s not owned by worker '%s' at epoch %d (already reassigned or finished)"
                            .formatted(taskId, worker, claimEpoch));
        }
        log.warn("task {} failed by {} (epoch {}): {}", taskId, worker, claimEpoch, truncated);
        return getTask(taskId);
    }

    /** 旧世代 / 非现任持有者的业务写入被栅栏拒绝。 */
    public static class FencingRejectedException extends IllegalStateException {
        public FencingRejectedException(String message) {
            super(message);
        }
    }

    /**
     * 文档 11.6：重诊环闭合 —— NOT_RECOVERED 后在同一事务内创建下一轮诊断任务
     * （调用方 saveVerification 是 @Transactional，本方法加入同一事务，原子衔接）。
     *
     * <ul>
     *   <li>轮次幂等键：diag-&lt;incidentId&gt;-r&lt;N&gt;（首轮是 diag-&lt;incidentId&gt;）——
     *       重复 verification 回调发现同键任务已存在时不再创建；</li>
     *   <li>not_before 退避：新任务到达 notBefore 前不出现在 pending 候选里，
     *       避免上一轮刚失败就立刻原样重跑；</li>
     *   <li>轮次上限：超过 max-rounds 停止自动重诊，写 REDIAGNOSIS_ESCALATED
     *       审计（人工升级待办），通知与 ACK 属通知通道职责。</li>
     * </ul>
     *
     * @return 新创建的任务；空表示「已达上限」或「重复回调」（区别写进审计/日志）
     */
    @Transactional
    public java.util.Optional<AgentTask> createRediagnosisTask(Long incidentId) {
        String baseKey = "diag-" + incidentId;
        int maxRound = 0;
        for (AgentTask t : agentTaskRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId)) {
            String key = t.getIdempotencyKey();
            if (key == null) {
                continue;
            }
            if (key.equals(baseKey)) {
                maxRound = Math.max(maxRound, 1);
            } else if (key.startsWith(baseKey + "-r")) {
                try {
                    maxRound = Math.max(maxRound, Integer.parseInt(key.substring(baseKey.length() + 2)));
                } catch (NumberFormatException ignore) {
                    // 非本轮次命名规则的任务，不参与轮次计算
                }
            }
        }
        int nextRound = maxRound + 1;
        String nextKey = baseKey + "-r" + nextRound;
        if (agentTaskRepository.findByIdempotencyKey(nextKey).isPresent()) {
            // 重复 verification 回调：同一轮任务已存在，不能多生成一轮
            log.info("re-diagnosis task {} already exists (duplicate verification callback), skip", nextKey);
            return java.util.Optional.empty();
        }
        if (nextRound > maxRediagnosisRounds) {
            log.warn("incident {} reached re-diagnosis cap ({} rounds) — escalation to human required",
                    incidentId, maxRediagnosisRounds);
            auditService.record(incidentId, "system", "REDIAGNOSIS_ESCALATED",
                    "rounds=" + maxRediagnosisRounds);
            return java.util.Optional.empty();
        }
        AgentTask task = new AgentTask(incidentId, AgentTask.TaskType.DIAGNOSIS,
                AgentTaskStatus.QUEUED, nextKey, Instant.now());
        task.setNotBefore(Instant.now().plusSeconds(rediagnosisBackoffSeconds));
        AgentTask saved = agentTaskRepository.save(task);
        log.info("re-diagnosis task {} created for incident {} (round {}, notBefore +{}s)",
                saved.getId(), incidentId, nextRound, rediagnosisBackoffSeconds);
        auditService.record(incidentId, "system", "REDIAGNOSIS_TASK_CREATED",
                "round=" + nextRound + ", key=" + nextKey);
        return java.util.Optional.of(saved);
    }

    @Scheduled(fixedDelayString = "${aisre.task.lease-reclaim-interval-ms:60000}")
    @Transactional
    public void reclaimExpiredLeases() {
        // 文档 6.5：优先按显式 lease_until 判过期；旧数据（null）回退 claimed_at+固定时长
        int reclaimed = agentTaskRepository.reclaimExpiredLeases(
                Instant.now(), Instant.now().minusSeconds(leaseSeconds), maxAttempts);
        if (reclaimed > 0) {
            log.warn("reclaimed {} expired diagnosis task lease(s)", reclaimed);
            // P1-MQ-03: 转入 DEAD 的即毒任务（DLQ 等价物）——审计 + 告警日志。
            // attempts == max 只在首次到达时成立 → 不重复审计
            for (AgentTask dead : agentTaskRepository.findByStatusAndAttemptsGreaterThanEqual(AgentTaskStatus.DEAD, maxAttempts)) {
                if (dead.getAttempts() != maxAttempts) {
                    continue;
                }
                log.error("POISON TASK: task {} (incident {}) moved to DEAD after {} attempts",
                        dead.getId(), dead.getIncidentId(), dead.getAttempts());
                auditService.record(dead.getIncidentId(), "system", "TASK_POISONED",
                        "attempts=" + dead.getAttempts());
            }
        }
    }

    private AgentTask getTask(Long taskId) {
        return agentTaskRepository.findById(taskId)
                .orElseThrow(() -> new IllegalArgumentException("AgentTask not found: " + taskId));
    }
}
