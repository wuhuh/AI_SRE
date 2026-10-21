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
@Table(name = "incident", indexes = {
        @Index(name = "idx_incident_status", columnList = "status"),
        @Index(name = "idx_incident_service", columnList = "service"),
        @Index(name = "idx_incident_started_at", columnList = "startedAt")
})
public class Incident {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** P1-CP-10: 乐观锁——并发状态推进（诊断回调 vs 人工 transition）丢更新防护。 */
    @jakarta.persistence.Version
    private Long version;

    @Column(nullable = false, length = 128)
    private String service;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private IncidentStatus status = IncidentStatus.DETECTED;

    @Column(nullable = false, length = 16)
    private String severity;

    @Column(length = 2048)
    private String summary;

    @Column(length = 2048)
    private String rootCause;

    @Column(length = 4096)
    private String recommendedActions;

    private Double confidence;

    // Agent 诊断语义（V13）：状态与降级原因必须落库，不能只活在 Agent 进程内。
    // UNKNOWN / TIMEOUT 不冒充 root cause，但 Incident 状态机仍保持兼容。
    @Column(length = 32)
    private String diagnosisStatus;

    @Column(length = 64)
    private String reasonCode;

    @Column(length = 1024)
    private String candidateRootCauses;

    private Boolean fallbackUsed;

    private Integer llmInputTokens;

    private Integer llmOutputTokens;

    @Column(nullable = false)
    private Instant startedAt;

    private Instant resolvedAt;

    @Column(nullable = false)
    private int alertCount = 0;

    // 文档 11.6：当前诊断轮次。NOT_RECOVERED 创建下一轮任务时推进；
    // verification 回调携带它验证的轮次，重放回调据此被识别并跳过。
    @Column(nullable = false)
    private int diagnosisRound = 0;

    public Incident() {
    }

    public Incident(String service, String severity, String summary, Instant startedAt) {
        this.service = service;
        this.severity = severity;
        this.summary = summary;
        this.startedAt = startedAt;
    }

    public Long getId() {
        return id;
    }

    public Long getVersion() {
        return version;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getService() {
        return service;
    }

    public void setService(String service) {
        this.service = service;
    }

    public IncidentStatus getStatus() {
        return status;
    }

    public void setStatus(IncidentStatus status) {
        this.status = status;
    }

    public String getSeverity() {
        return severity;
    }

    public void setSeverity(String severity) {
        this.severity = severity;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getRootCause() {
        return rootCause;
    }

    public void setRootCause(String rootCause) {
        this.rootCause = rootCause;
    }

    public String getRecommendedActions() {
        return recommendedActions;
    }

    public void setRecommendedActions(String recommendedActions) {
        this.recommendedActions = recommendedActions;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(Instant startedAt) {
        this.startedAt = startedAt;
    }

    public Instant getResolvedAt() {
        return resolvedAt;
    }

    public void setResolvedAt(Instant resolvedAt) {
        this.resolvedAt = resolvedAt;
    }


    public int getAlertCount() {
        return alertCount;
    }

    public void setAlertCount(int alertCount) {
        this.alertCount = alertCount;
    }

    public int getDiagnosisRound() {
        return diagnosisRound;
    }

    public void setDiagnosisRound(int diagnosisRound) {
        this.diagnosisRound = diagnosisRound;
    }

    public String getDiagnosisStatus() {
        return diagnosisStatus;
    }

    public void setDiagnosisStatus(String diagnosisStatus) {
        this.diagnosisStatus = diagnosisStatus;
    }

    public String getReasonCode() {
        return reasonCode;
    }

    public void setReasonCode(String reasonCode) {
        this.reasonCode = reasonCode;
    }

    public String getCandidateRootCauses() {
        return candidateRootCauses;
    }

    public void setCandidateRootCauses(String candidateRootCauses) {
        this.candidateRootCauses = candidateRootCauses;
    }

    public Boolean getFallbackUsed() {
        return fallbackUsed;
    }

    public void setFallbackUsed(Boolean fallbackUsed) {
        this.fallbackUsed = fallbackUsed;
    }

    public Integer getLlmInputTokens() {
        return llmInputTokens;
    }

    public void setLlmInputTokens(Integer llmInputTokens) {
        this.llmInputTokens = llmInputTokens;
    }

    public Integer getLlmOutputTokens() {
        return llmOutputTokens;
    }

    public void setLlmOutputTokens(Integer llmOutputTokens) {
        this.llmOutputTokens = llmOutputTokens;
    }
}