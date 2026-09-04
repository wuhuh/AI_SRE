package com.aisre.repo;

import com.aisre.domain.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    List<AuditLog> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);
}