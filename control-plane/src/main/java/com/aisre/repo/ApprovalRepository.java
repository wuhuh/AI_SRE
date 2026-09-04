package com.aisre.repo;

import com.aisre.domain.Approval;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ApprovalRepository extends JpaRepository<Approval, Long> {

    List<Approval> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);

    List<Approval> findByIncidentIdAndStatus(Long incidentId, String status);
}