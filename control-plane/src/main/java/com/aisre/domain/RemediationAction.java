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
@Table(name = "remediation_action", indexes = {
        @Index(name = "idx_remediation_incident", columnList = "incidentId"),
        @Index(name = "idx_remediation_status", columnList = "status")
})
public class RemediationAction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long incidentId;

    @Column(nullable = false, length = 128)
    private String toolName;

    @Column(nullable = false, length = 4096)
    private String argumentsJson;

    @Column(nullable = false, length = 16)
    private String status;

    private Long approvalId;

    @Column(nullable = false, length = 4096)
    private String resultSummary;

    @Column(nullable = false)
    private Instant createdAt;

    private Instant executedAt;

    public RemediationAction() {
    }

    public RemediationAction(Long incidentId, String toolName, String argumentsJson,
                             String status, Long approvalId, String resultSummary,
                             Instant createdAt) {
        this.incidentId = incidentId;
        this.toolName = toolName;
        this.argumentsJson = argumentsJson;
        this.status = status;
        this.approvalId = approvalId;
        this.resultSummary = resultSummary;
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

    public String getToolName() {
        return toolName;
    }

    public void setToolName(String toolName) {
        this.toolName = toolName;
    }

    public String getArgumentsJson() {
        return argumentsJson;
    }

    public void setArgumentsJson(String argumentsJson) {
        this.argumentsJson = argumentsJson;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Long getApprovalId() {
        return approvalId;
    }

    public void setApprovalId(Long approvalId) {
        this.approvalId = approvalId;
    }

    public String getResultSummary() {
        return resultSummary;
    }

    public void setResultSummary(String resultSummary) {
        this.resultSummary = resultSummary;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getExecutedAt() {
        return executedAt;
    }

    public void setExecutedAt(Instant executedAt) {
        this.executedAt = executedAt;
    }
}