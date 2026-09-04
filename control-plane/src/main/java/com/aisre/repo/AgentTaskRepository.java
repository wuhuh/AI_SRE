package com.aisre.repo;

import com.aisre.domain.AgentTask;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AgentTaskRepository extends JpaRepository<AgentTask, Long> {

    List<AgentTask> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);

    Optional<AgentTask> findByIdempotencyKey(String idempotencyKey);

    List<AgentTask> findByStatusOrderByCreatedAtAsc(String status);
}