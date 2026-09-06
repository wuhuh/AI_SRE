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
@Table(name = "approval", indexes = {
        @Index(name = "idx_approval_incident", columnList = "incidentId"),
        @Index(name = "idx_approval_status", columnList = "status")
})
public class Approval {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long incidentId;

    @Column(nullable = false, length = 128)
    private String actionType;

    @Column(nullable = false, length = 4096)
    private String actionPayload;

    @Column(nullable = false, length = 16)
    private String status;

    @Column(length = 64)
    private String requestedBy;

    @Column(length = 64)
    private String decidedBy;

    @Column(length = 1024)
    private String comment;

    @Column(nullable = false)
    private Instant createdAt;

    private Instant decidedAt;

    @Column(length = 64)
    private String executionToken;

    /** P1-CP-12: 审批过期时间（PENDING 超过即不可再决定）。 */
    private Instant expiresAt;

    public Approval() {
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Instant expiresAt) {
        this.expiresAt = expiresAt;
    }

    public Approval(Long incidentId, String actionType, String actionPayload, String status,
                    String requestedBy, Instant createdAt) {
        this.incidentId = incidentId;
        this.actionType = actionType;
        this.actionPayload = actionPayload;
        this.status = status;
        this.requestedBy = requestedBy;
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

    public String getActionType() {
        return actionType;
    }

    public void setActionType(String actionType) {
        this.actionType = actionType;
    }

    public String getActionPayload() {
        return actionPayload;
    }

    public void setActionPayload(String actionPayload) {
        this.actionPayload = actionPayload;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getRequestedBy() {
        return requestedBy;
    }

    public void setRequestedBy(String requestedBy) {
        this.requestedBy = requestedBy;
    }

    public String getDecidedBy() {
        return decidedBy;
    }

    public void setDecidedBy(String decidedBy) {
        this.decidedBy = decidedBy;
    }

    public String getComment() {
        return comment;
    }

    public void setComment(String comment) {
        this.comment = comment;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getDecidedAt() {
        return decidedAt;
    }

    public void setDecidedAt(Instant decidedAt) {
        this.decidedAt = decidedAt;
    }

    public String getExecutionToken() {
        return executionToken;
    }

    public void setExecutionToken(String executionToken) {
        this.executionToken = executionToken;
    }
}