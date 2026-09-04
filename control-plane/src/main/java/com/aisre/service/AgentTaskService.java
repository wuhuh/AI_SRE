package com.aisre.service;

import com.aisre.domain.AgentTask;
import com.aisre.repo.AgentTaskRepository;
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

    private final AgentTaskRepository agentTaskRepository;
    private final long leaseSeconds;

    public AgentTaskService(AgentTaskRepository agentTaskRepository,
                            @Value("${aisre.task.lease-seconds:600}") long leaseSeconds) {
        this.agentTaskRepository = agentTaskRepository;
        this.leaseSeconds = leaseSeconds;
    }

    @Transactional
    public Optional<AgentTask> claim(Long taskId, String worker) {
        int claimed = agentTaskRepository.claimTask(taskId, worker, Instant.now());
        if (claimed == 0) {
            return Optional.empty();
        }
        return agentTaskRepository.findById(taskId);
    }

    @Transactional
    public AgentTask complete(Long taskId) {
        AgentTask task = getTask(taskId);
        task.setStatus("COMPLETED");
        task.setFinishedAt(Instant.now());
        return agentTaskRepository.save(task);
    }

    @Transactional
    public AgentTask fail(Long taskId, String error) {
        AgentTask task = getTask(taskId);
        task.setStatus("FAILED");
        task.setError(error == null ? "unknown error" : error.substring(0, Math.min(error.length(), 4000)));
        task.setFinishedAt(Instant.now());
        return agentTaskRepository.save(task);
    }

    @Scheduled(fixedDelayString = "${aisre.task.lease-reclaim-interval-ms:60000}")
    @Transactional
    public void reclaimExpiredLeases() {
        agentTaskRepository.reclaimExpiredLeases(Instant.now().minusSeconds(leaseSeconds));
    }

    private AgentTask getTask(Long taskId) {
        return agentTaskRepository.findById(taskId)
                .orElseThrow(() -> new IllegalArgumentException("AgentTask not found: " + taskId));
    }
}
