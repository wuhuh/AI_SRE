package com.aisre.repo;

import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface IncidentRepository extends JpaRepository<Incident, Long> {

    List<Incident> findByStatusOrderByStartedAtDesc(IncidentStatus status);

    List<Incident> findByServiceContainingIgnoreCaseOrderByStartedAtDesc(String service);
}