package com.aisre.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "agent_task", indexes = {
        @Index(name = "idx_agent_task_incident", columnList = "incidentId"),
        @Index(name = "idx_agent_task_status", columnList = "status")
})
public class AgentTask {

    public enum TaskType {
        DIAGNOSIS,
        VERIFICATION
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long incidentId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private TaskType type;

    // P3-CP-25: 状态枚举化
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private AgentTaskStatus status;

    @Column(nullable = false, length = 64)
    private String idempotencyKey;

    @Column(nullable = false)
    private Instant createdAt;

    private Instant startedAt;

    private Instant finishedAt;

    @Column(length = 4096)
    private String resultJson;

    @Column(length = 4096)
    private String error;

    // P1-MQ-02: claim/lease —— 多副本消费时条件更新抢占，防止重复诊断/重复修复
    @Column(length = 64)
    private String claimedBy;

    private Instant claimedAt;

    // P1-CP-07: outbox 投递状态（PENDING→SENT；发送失败/崩溃由扫描器补发）
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private MqStatus mqStatus = MqStatus.PENDING;

    @Column(nullable = false)
    private int mqAttempts = 0;

    // P1-MQ-03: 租约回收重试计数（达上限 → DEAD，DLQ 等价物）
    @Column(nullable = false)
    private int attempts = 0;

    public int getAttempts() {
        return attempts;
    }

    public void setAttempts(int attempts) {
        this.attempts = attempts;
    }

    public MqStatus getMqStatus() {
        return mqStatus;
    }

    public void setMqStatus(MqStatus mqStatus) {
        this.mqStatus = mqStatus;
    }

    public int getMqAttempts() {
        return mqAttempts;
    }

    public void setMqAttempts(int mqAttempts) {
        this.mqAttempts = mqAttempts;
    }

    public AgentTask() {
    }

    public AgentTask(Long incidentId, TaskType type, AgentTaskStatus status, String idempotencyKey, Instant createdAt) {
        this.incidentId = incidentId;
        this.type = type;
        this.status = status;
        this.idempotencyKey = idempotencyKey;
        this.createdAt = createdAt;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getIncidentId() {
        return incidentId;
    }

    public void setIncidentId(Long incidentId) {
        this.incidentId = incidentId;
    }

    public TaskType getType() {
        return type;
    }

    public void setType(TaskType type) {
        this.type = type;
    }

    public AgentTaskStatus getStatus() {
        return status;
    }

    public void setStatus(AgentTaskStatus status) {
        this.status = status;
    }

    public String getIdempotencyKey() {
        return idempotencyKey;
    }

    public void setIdempotencyKey(String idempotencyKey) {
        this.idempotencyKey = idempotencyKey;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(Instant startedAt) {
        this.startedAt = startedAt;
    }

    public Instant getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(Instant finishedAt) {
        this.finishedAt = finishedAt;
    }

    public String getResultJson() {
        return resultJson;
    }

    public void setResultJson(String resultJson) {
        this.resultJson = resultJson;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }

    public String getClaimedBy() {
        return claimedBy;
    }

    public void setClaimedBy(String claimedBy) {
        this.claimedBy = claimedBy;
    }

    public Instant getClaimedAt() {
        return claimedAt;
    }

    public void setClaimedAt(Instant claimedAt) {
        this.claimedAt = claimedAt;
    }
}