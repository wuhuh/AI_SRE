package com.aisre.repo;

import com.aisre.domain.ToolCall;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ToolCallRepository extends JpaRepository<ToolCall, Long> {

    List<ToolCall> findByIncidentIdOrderByCreatedAtAsc(Long incidentId);
}