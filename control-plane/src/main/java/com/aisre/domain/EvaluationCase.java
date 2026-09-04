package com.aisre.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;

@Entity
@Table(name = "evaluation_case", indexes = {
        @Index(name = "idx_eval_fault_type", columnList = "faultType"),
        @Index(name = "idx_eval_service", columnList = "service")
})
public class EvaluationCase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 128)
    private String caseId;

    @Column(nullable = false, length = 128)
    private String faultType;

    @Column(nullable = false, length = 128)
    private String service;

    @Column(nullable = false, length = 1024)
    private String expectedRootCause;

    @Column(nullable = false, length = 4096)
    private String expectedEvidence;

    public EvaluationCase() {
    }

    public EvaluationCase(String caseId, String faultType, String service,
                          String expectedRootCause, String expectedEvidence) {
        this.caseId = caseId;
        this.faultType = faultType;
        this.service = service;
        this.expectedRootCause = expectedRootCause;
        this.expectedEvidence = expectedEvidence;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getCaseId() {
        return caseId;
    }

    public void setCaseId(String caseId) {
        this.caseId = caseId;
    }

    public String getFaultType() {
        return faultType;
    }

    public void setFaultType(String faultType) {
        this.faultType = faultType;
    }

    public String getService() {
        return service;
    }

    public void setService(String service) {
        this.service = service;
    }

    public String getExpectedRootCause() {
        return expectedRootCause;
    }

    public void setExpectedRootCause(String expectedRootCause) {
        this.expectedRootCause = expectedRootCause;
    }

    public String getExpectedEvidence() {
        return expectedEvidence;
    }

    public void setExpectedEvidence(String expectedEvidence) {
        this.expectedEvidence = expectedEvidence;
    }
}