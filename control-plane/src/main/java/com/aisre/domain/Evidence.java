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
@Table(name = "evidence", indexes = {
        @Index(name = "idx_evidence_incident", columnList = "incidentId"),
        @Index(name = "idx_evidence_task", columnList = "taskId")
})
public class Evidence {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long incidentId;

    private Long taskId;

    @Column(nullable = false, length = 64)
    private String source;

    @Column(nullable = false, length = 128)
    private String evidenceKey;

    @Column(nullable = false, length = 4096)
    private String content;

    // P2-AR-09: 溯源字段（查询语句/时间范围）
    @Column(length = 1024)
    private String query;

    @Column(length = 64)
    private String timeRange;

    @Column(nullable = false)
    private Instant collectedAt;

    public Evidence() {
    }

    public Evidence(Long incidentId, Long taskId, String source, String evidenceKey,
                    String content, Instant collectedAt) {
        this(incidentId, taskId, source, evidenceKey, content, null, null, collectedAt);
    }

    public Evidence(Long incidentId, Long taskId, String source, String evidenceKey,
                    String content, String query, String timeRange, Instant collectedAt) {
        this.incidentId = incidentId;
        this.taskId = taskId;
        this.source = source;
        this.evidenceKey = evidenceKey;
        this.content = content;
        this.query = query;
        this.timeRange = timeRange;
        this.collectedAt = collectedAt;
    }

    public String getQuery() {
        return query;
    }

    public String getTimeRange() {
        return timeRange;
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

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getEvidenceKey() {
        return evidenceKey;
    }

    public void setEvidenceKey(String evidenceKey) {
        this.evidenceKey = evidenceKey;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public Instant getCollectedAt() {
        return collectedAt;
    }

    public void setCollectedAt(Instant collectedAt) {
        this.collectedAt = collectedAt;
    }
}