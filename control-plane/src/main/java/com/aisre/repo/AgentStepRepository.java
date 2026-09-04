package com.aisre.repo;

import com.aisre.domain.AgentStep;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AgentStepRepository extends JpaRepository<AgentStep, Long> {

    List<AgentStep> findByIncidentIdOrderByStepOrderAsc(Long incidentId);

    List<AgentStep> findByTaskIdOrderByStepOrderAsc(Long taskId);
}