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
@Table(name = "alert", indexes = {
        @Index(name = "idx_alert_fingerprint", columnList = "fingerprint"),
        @Index(name = "idx_alert_received_at", columnList = "receivedAt"),
        @Index(name = "idx_alert_incident_id", columnList = "incidentId")
})
public class Alert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 128)
    private String fingerprint;

    @Column(nullable = false, length = 128)
    private String service;

    @Column(name = "alert_name", nullable = false, length = 128)
    private String alertName;

    @Column(nullable = false, length = 256)
    private String resource;

    @Column(nullable = false, length = 16)
    private String severity;

    @Column(length = 2048)
    private String summary;

    @Column(length = 4096)
    private String rawBody;

    @Column(nullable = false)
    private Instant receivedAt;

    private Long incidentId;

    public Alert() {
    }

    public Alert(String fingerprint, String service, String alertName, String resource,
                 String severity, String summary, String rawBody, Instant receivedAt) {
        this.fingerprint = fingerprint;
        this.service = service;
        this.alertName = alertName;
        this.resource = resource;
        this.severity = severity;
        this.summary = summary;
        this.rawBody = rawBody;
        this.receivedAt = receivedAt;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getFingerprint() {
        return fingerprint;
    }

    public void setFingerprint(String fingerprint) {
        this.fingerprint = fingerprint;
    }

    public String getService() {
        return service;
    }

    public void setService(String service) {
        this.service = service;
    }

    public String getAlertName() {
        return alertName;
    }

    public void setAlertName(String alertName) {
        this.alertName = alertName;
    }

    public String getResource() {
        return resource;
    }

    public void setResource(String resource) {
        this.resource = resource;
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

    public String getRawBody() {
        return rawBody;
    }

    public void setRawBody(String rawBody) {
        this.rawBody = rawBody;
    }

    public Instant getReceivedAt() {
        return receivedAt;
    }

    public void setReceivedAt(Instant receivedAt) {
        this.receivedAt = receivedAt;
    }

    public Long getIncidentId() {
        return incidentId;
    }

    public void setIncidentId(Long incidentId) {
        this.incidentId = incidentId;
    }
}