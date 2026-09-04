package com.aisre.repo;

import com.aisre.domain.Evidence;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface EvidenceRepository extends JpaRepository<Evidence, Long> {

    List<Evidence> findByIncidentIdOrderByCollectedAtAsc(Long incidentId);
}