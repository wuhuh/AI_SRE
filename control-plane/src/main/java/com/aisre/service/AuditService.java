package com.aisre.service;

import com.aisre.domain.AuditLog;
import com.aisre.repo.AuditLogRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    public AuditService(AuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    public void record(Long incidentId, String actor, String action, String detail) {
        auditLogRepository.save(new AuditLog(incidentId, actor, action, detail, Instant.now()));
    }
}