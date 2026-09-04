package com.aisre.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "tool_call", indexes = {
        @Index(name = "idx_tool_call_incident", columnList = "incidentId"),
        @Index(name = "idx_tool_call_task", columnList = "taskId"),
        @Index(name = "idx_tool_call_name", columnList = "toolName")
})
public class ToolCall {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long incidentId;

    private Long taskId;

    @Column(nullable = false, length = 128)
    private String toolName;

    @Column(nullable = false, length = 32)
    private String riskLevel;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(nullable = false, length = 4096)
    private String argumentsJson;

    @Column(length = 8192)
    private String resultSummary;

    private Long durationMs;

    @Column(length = 2048)
    private String error;

    @Column(nullable = false)
    private Instant createdAt;

    public ToolCall() {
    }

    public ToolCall(Long incidentId, Long taskId, String toolName, String riskLevel,
                    String status, String argumentsJson, String resultSummary,
                    Long durationMs, String error, Instant createdAt) {
        this.incidentId = incidentId;
        this.taskId = taskId;
        this.toolName = toolName;
        this.riskLevel = riskLevel;
        this.status = status;
        this.argumentsJson = argumentsJson;
        this.resultSummary = resultSummary;
        this.durationMs = durationMs;
        this.error = error;
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

    public Long getTaskId() {
        return taskId;
    }

    public void setTaskId(Long taskId) {
        this.taskId = taskId;
    }

    public String getToolName() {
        return toolName;
    }

    public void setToolName(String toolName) {
        this.toolName = toolName;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public void setRiskLevel(String riskLevel) {
        this.riskLevel = riskLevel;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getArgumentsJson() {
        return argumentsJson;
    }

    public void setArgumentsJson(String argumentsJson) {
        this.argumentsJson = argumentsJson;
    }

    public String getResultSummary() {
        return resultSummary;
    }

    public void setResultSummary(String resultSummary) {
        this.resultSummary = resultSummary;
    }

    public Long getDurationMs() {
        return durationMs;
    }

    public void setDurationMs(Long durationMs) {
        this.durationMs = durationMs;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }
}