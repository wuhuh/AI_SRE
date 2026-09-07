package com.aisre.service;

import com.aisre.domain.AgentTask;
import com.aisre.domain.AgentTaskStatus;
import com.aisre.domain.MqStatus;
import com.aisre.repo.AgentTaskRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.common.message.Message;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * P1-CP-07: outbox 模式解 MQ 双写原子性——
 * 1. 任务行（mq_status=PENDING）随业务事务提交，MQ 发送移到 afterCommit；
 * 2. 发送失败/提交后崩溃由后台扫描器按 mq_attempts 补发（有上限）；
 * 3. producer 启动失败不再炸应用启动（解耦），发送时懒重连。
 */
@Service
public class RocketMqAgentJobProducer implements AgentJobProducer {

    public static final String DIAGNOSIS_TOPIC = "aisre-agent-task";

    private static final Logger log = LoggerFactory.getLogger(RocketMqAgentJobProducer.class);

    private final AgentTaskRepository agentTaskRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final int maxSendAttempts;
    private final org.springframework.transaction.support.TransactionTemplate requiresNewTx;
    private DefaultMQProducer producer;

    public RocketMqAgentJobProducer(AgentTaskRepository agentTaskRepository,
                                    @Value("${aisre.task.max-send-attempts:20}") int maxSendAttempts,
                                    org.springframework.transaction.PlatformTransactionManager transactionManager) {
        this.agentTaskRepository = agentTaskRepository;
        this.maxSendAttempts = maxSendAttempts;
        this.requiresNewTx = new org.springframework.transaction.support.TransactionTemplate(transactionManager);
        this.requiresNewTx.setPropagationBehavior(
                org.springframework.transaction.support.TransactionTemplate.PROPAGATION_REQUIRES_NEW);
    }

    @PostConstruct
    public void start() {
        startProducerQuietly();
    }

    private void startProducerQuietly() {
        if (producer != null) {
            return;
        }
        try {
            producer = new DefaultMQProducer("aisre-control-plane");
            producer.setNamesrvAddr(System.getenv().getOrDefault("ROCKETMQ_NAME_SERVER", "localhost:9876"));
            producer.setSendMsgTimeout(3000);
            producer.start();
            log.info("RocketMQ producer started");
        } catch (Exception e) {
            // P1-CP-07: producer 起不来不炸启动；任务留在 outbox 由扫描器补发
            producer = null;
            log.error("RocketMQ producer start failed; tasks stay in outbox until it recovers: {}", e.getMessage());
        }
    }

    @PreDestroy
    public void stop() {
        if (producer != null) {
            producer.shutdown();
        }
    }

    @Override
    public void sendDiagnosisTask(Long incidentId) {
        // P1-CP-08: 幂等键去 UUID——首键 diag-<incidentId>，重试键带序号
        String baseKey = "diag-" + incidentId;
        AgentTask existing = agentTaskRepository.findTopByIdempotencyKeyOrderByIdDesc(baseKey).orElse(null);
        if (existing != null && existing.getStatus() != AgentTaskStatus.FAILED) {
            log.info("diagnosis task for incident {} already exists ({}), skip re-dispatch",
                    incidentId, existing.getStatus());
            return;
        }
        long attemptNo = agentTaskRepository.findByIncidentIdOrderByCreatedAtAsc(incidentId).stream()
                .filter(t -> t.getIdempotencyKey().startsWith(baseKey)).count();
        String idempotencyKey = attemptNo == 0 ? baseKey : baseKey + "-r" + attemptNo;

        AgentTask task = new AgentTask(
                incidentId,
                AgentTask.TaskType.DIAGNOSIS,
                AgentTaskStatus.QUEUED,
                idempotencyKey,
                Instant.now()
        );
        task.setMqStatus(MqStatus.PENDING);
        task = agentTaskRepository.save(task);
        final Long taskId = task.getId();
        // P1-CP-07: 提交后再发；发送失败/提交后崩溃由扫描器补发。
        // P1-CP-11: afterCommit 里的写必须 REQUIRES_NEW（REQUIRED 会进死事务静默丢失）
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    requiresNewTx.executeWithoutResult(status -> attemptSend(taskId));
                }
            });
        } else {
            attemptSend(taskId);
        }
    }

    private void attemptSend(Long taskId) {
        AgentTask task = agentTaskRepository.findById(taskId).orElse(null);
        if (task == null || "SENT".equals(task.getMqStatus())) {
            return;
        }
        startProducerQuietly();
        if (producer == null) {
            task.setMqAttempts(task.getMqAttempts() + 1);
            agentTaskRepository.save(task);
            return;
        }
        try {
            Map<String, Object> payload = Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "taskId", String.valueOf(task.getId()),
                    "incidentId", String.valueOf(task.getIncidentId()),
                    "type", task.getType().name(),
                    "createdAt", Instant.now().toString(),
                    "traceId", "",
                    "version", 1
            );
            Message message = new Message(DIAGNOSIS_TOPIC, String.valueOf(task.getId()),
                    objectMapper.writeValueAsBytes(payload));
            producer.send(message);
            task.setMqStatus(MqStatus.SENT);
            agentTaskRepository.save(task);
        } catch (Exception e) {
            task.setMqAttempts(task.getMqAttempts() + 1);
            agentTaskRepository.save(task);
            log.warn("send agent task {} failed (attempt {}): {}",
                    taskId, task.getMqAttempts(), e.getMessage());
        }
    }

    @Scheduled(fixedDelayString = "${aisre.task.outbox-scan-interval-ms:10000}")
    public void flushOutbox() {
        List<AgentTask> pending = agentTaskRepository.findByMqStatusAndMqAttemptsLessThan(MqStatus.PENDING, maxSendAttempts);
        for (AgentTask task : pending) {
            attemptSend(task.getId());
        }
    }
}
