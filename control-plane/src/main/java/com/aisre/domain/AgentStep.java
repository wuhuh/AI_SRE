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
@Table(name = "agent_step", indexes = {
        @Index(name = "idx_agent_step_task", columnList = "taskId"),
        @Index(name = "idx_agent_step_incident", columnList = "incidentId")
})
public class AgentStep {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long taskId;

    @Column(nullable = false)
    private Long incidentId;

    @Column(nullable = false)
    private Integer stepOrder;

    @Column(nullable = false, length = 64)
    private String stepType;

    @Column(nullable = false, length = 64)
    private String status;

    @Column(length = 4096)
    private String inputSummary;

    @Column(length = 8192)
    private String outputSummary;

    @Column(nullable = false)
    private Instant createdAt;

    public AgentStep() {
    }

    public AgentStep(Long taskId, Long incidentId, Integer stepOrder, String stepType,
                     String status, String inputSummary, String outputSummary, Instant createdAt) {
        this.taskId = taskId;
        this.incidentId = incidentId;
        this.stepOrder = stepOrder;
        this.stepType = stepType;
        this.status = status;
        this.inputSummary = inputSummary;
        this.outputSummary = outputSummary;
        this.createdAt = createdAt;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getTaskId() {
        return taskId;
    }

    public void setTaskId(Long taskId) {
        this.taskId = taskId;
    }

    public Long getIncidentId() {
        return incidentId;
    }

    public void setIncidentId(Long incidentId) {
        this.incidentId = incidentId;
    }

    public Integer getStepOrder() {
        return stepOrder;
    }

    public void setStepOrder(Integer stepOrder) {
        this.stepOrder = stepOrder;
    }

    public String getStepType() {
        return stepType;
    }

    public void setStepType(String stepType) {
        this.stepType = stepType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getInputSummary() {
        return inputSummary;
    }

    public void setInputSummary(String inputSummary) {
        this.inputSummary = inputSummary;
    }

    public String getOutputSummary() {
        return outputSummary;
    }

    public void setOutputSummary(String outputSummary) {
        this.outputSummary = outputSummary;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }
}