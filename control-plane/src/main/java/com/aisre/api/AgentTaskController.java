package com.aisre.api;

import com.aisre.domain.AgentTask;
import com.aisre.domain.AgentTaskStatus;
import com.aisre.repo.AgentTaskRepository;
import com.aisre.service.AgentTaskService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/v1/tasks")
public class AgentTaskController {

    private final AgentTaskRepository agentTaskRepository;
    private final AgentTaskService agentTaskService;

    public AgentTaskController(AgentTaskRepository agentTaskRepository, AgentTaskService agentTaskService) {
        this.agentTaskRepository = agentTaskRepository;
        this.agentTaskService = agentTaskService;
    }

    @GetMapping("/pending")
    public List<AgentTask> pending() {
        return agentTaskRepository.findByStatusOrderByCreatedAtAsc(AgentTaskStatus.QUEUED);
    }

    /**
     * P1-MQ-02: 原子领取。多副本消费者先 claim 再诊断；
     * 返回 {"claimed": true, "task": {...}} 或 {"claimed": false}。
     */
    @PostMapping("/{id}/claim")
    public Map<String, Object> claim(@PathVariable Long id,
                                     @RequestBody(required = false) Map<String, String> body) {
        String worker = body == null || body.get("worker") == null ? "unknown-worker" : body.get("worker");
        Optional<AgentTask> claimed = agentTaskService.claim(id, worker);
        return claimed
                .<Map<String, Object>>map(task -> Map.of("claimed", true, "task", task))
                .orElseGet(() -> Map.of("claimed", false));
    }

    @PostMapping("/{id}/complete")
    public AgentTask complete(@PathVariable Long id) {
        return agentTaskService.complete(id);
    }

    /** P1-MQ-02: 失败终态（worker 侧异常上报），避免任务卡死在 RUNNING。 */
    @PostMapping("/{id}/fail")
    public AgentTask fail(@PathVariable Long id, @RequestBody(required = false) Map<String, String> body) {
        return agentTaskService.fail(id, body == null ? null : body.get("error"));
    }
}
