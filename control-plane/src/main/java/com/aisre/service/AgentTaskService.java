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

    public AgentTaskService(AgentTaskRepository agentTaskRepository,
                            com.aisre.service.AuditService auditService,
                            @Value("${aisre.task.lease-seconds:600}") long leaseSeconds,
                            @Value("${aisre.task.max-attempts:16}") int maxAttempts) {
        this.agentTaskRepository = agentTaskRepository;
        this.auditService = auditService;
        this.leaseSeconds = leaseSeconds;
        this.maxAttempts = maxAttempts;
    }

    @Transactional
    public Optional<AgentTask> claim(Long taskId, String worker) {
        int claimed = agentTaskRepository.claimTask(taskId, worker, Instant.now());
        if (claimed == 0) {
            log.debug("task {} claim missed by {} (already claimed)", taskId, worker);
            return Optional.empty();
        }
        log.info("task {} claimed by {}", taskId, worker);
        return agentTaskRepository.findById(taskId);
    }

    @Transactional
    public AgentTask complete(Long taskId) {
        AgentTask task = getTask(taskId);
        task.setStatus(AgentTaskStatus.COMPLETED);
        task.setFinishedAt(Instant.now());
        return agentTaskRepository.save(task);
    }

    @Transactional
    public AgentTask fail(Long taskId, String error) {
        AgentTask task = getTask(taskId);
        task.setStatus(AgentTaskStatus.FAILED);
        task.setError(error == null ? "unknown error" : error.substring(0, Math.min(error.length(), 4000)));
        task.setFinishedAt(Instant.now());
        log.warn("task {} failed: {}", taskId, task.getError());
        return agentTaskRepository.save(task);
    }

    @Scheduled(fixedDelayString = "${aisre.task.lease-reclaim-interval-ms:60000}")
    @Transactional
    public void reclaimExpiredLeases() {
        int reclaimed = agentTaskRepository.reclaimExpiredLeases(
                Instant.now().minusSeconds(leaseSeconds), maxAttempts);
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
