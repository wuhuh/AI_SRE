package com.aisre.domain;

public enum IncidentStatus {
    DETECTED,
    TRIAGING,
    DIAGNOSING,
    ROOT_CAUSE_FOUND,
    WAITING_APPROVAL,
    REMEDIATING,
    VERIFYING,
    RESOLVED,
    FAILED
}