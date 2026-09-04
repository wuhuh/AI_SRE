package com.aisre.service;

import com.aisre.domain.AgentTask;
import com.aisre.repo.AgentTaskRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.common.message.Message;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@Service
public class RocketMqAgentJobProducer implements AgentJobProducer {

    public static final String DIAGNOSIS_TOPIC = "aisre-agent-task";

    private final AgentTaskRepository agentTaskRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private DefaultMQProducer producer;

    public RocketMqAgentJobProducer(AgentTaskRepository agentTaskRepository) {
        this.agentTaskRepository = agentTaskRepository;
    }

    @PostConstruct
    public void start() throws Exception {
        producer = new DefaultMQProducer("aisre-control-plane");
        producer.setNamesrvAddr(System.getenv().getOrDefault("ROCKETMQ_NAME_SERVER", "localhost:9876"));
        producer.setSendMsgTimeout(3000);
        producer.start();
    }

    @PreDestroy
    public void stop() {
        if (producer != null) {
            producer.shutdown();
        }
    }

    @Override
    public void sendDiagnosisTask(Long incidentId) {
        String idempotencyKey = "diag-" + incidentId + "-" + UUID.randomUUID();
        AgentTask task = new AgentTask(
                incidentId,
                AgentTask.TaskType.DIAGNOSIS,
                "QUEUED",
                idempotencyKey,
                Instant.now()
        );
        agentTaskRepository.save(task);
        try {
            String eventId = UUID.randomUUID().toString();
            Map<String, Object> payload = Map.of(
                    "eventId", eventId,
                    "taskId", String.valueOf(task.getId()),
                    "incidentId", String.valueOf(incidentId),
                    "type", "DIAGNOSIS",
                    "createdAt", Instant.now().toString(),
                    "traceId", "",
                    "version", 1
            );
            byte[] body = objectMapper.writeValueAsBytes(payload);
            Message message = new Message(DIAGNOSIS_TOPIC, String.valueOf(task.getId()), body);
            producer.send(message);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to send agent task to RocketMQ", e);
        }
    }
}