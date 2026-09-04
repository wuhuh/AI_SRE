package com.aisre.repo;

import com.aisre.domain.RemediationAction;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RemediationActionRepository extends JpaRepository<RemediationAction, Long> {

    List<RemediationAction> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);
}