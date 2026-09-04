package com.aisre.api;

import com.aisre.domain.AgentTask;
import com.aisre.repo.AgentTaskRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/tasks")
public class AgentTaskController {

    private final AgentTaskRepository agentTaskRepository;

    public AgentTaskController(AgentTaskRepository agentTaskRepository) {
        this.agentTaskRepository = agentTaskRepository;
    }

    @GetMapping("/pending")
    public List<AgentTask> pending() {
        return agentTaskRepository.findByStatusOrderByCreatedAtAsc("QUEUED");
    }

    @PostMapping("/{id}/complete")
    public AgentTask complete(@PathVariable Long id) {
        AgentTask task = agentTaskRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("AgentTask not found: " + id));
        task.setStatus("COMPLETED");
        task.setFinishedAt(Instant.now());
        return agentTaskRepository.save(task);
    }
}