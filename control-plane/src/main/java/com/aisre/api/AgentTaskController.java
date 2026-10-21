package com.aisre.api;

import com.aisre.domain.AgentTask;
import com.aisre.repo.AgentTaskRepository;
import com.aisre.service.AgentTaskService;
import com.aisre.service.AgentTaskService.FencingRejectedException;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
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

    /**
     * 文档 11.6：QUEUED 且已过 not_before 的任务才进入候选——
     * 重诊任务带退避时间，未到期不派发。
     */
    @GetMapping("/pending")
    public List<AgentTask> pending(@RequestParam(defaultValue = "50") int limit) {
        // 有界批量：积压时不让一次轮询把整张任务表拉回 Agent；
        // claim 仍是原子抢占，多副本并发领取不会重复执行。
        int safeLimit = Math.min(Math.max(1, limit), 500);
        return agentTaskRepository.findClaimableQueued(
                Instant.now(), PageRequest.of(0, safeLimit));
    }

    /** 队列深度（DB 事实源），供 Agent 的 aisre_tasks_pending 指标使用。 */
    @GetMapping("/pending/count")
    public Map<String, Long> pendingCount() {
        return Map.of("count", agentTaskRepository.countClaimableQueued(Instant.now()));
    }

    /**
     * P1-MQ-02: 原子领取。多副本消费者先 claim 再诊断；
     * 返回 {"claimed": true, "task": {...}} 或 {"claimed": false}。
     * 文档 6.7：task 内含 claimEpoch，worker 后续所有业务写入必须携带它。
     */
    @PostMapping("/{id}/claim")
    public Map<String, Object> claim(@PathVariable Long id,
                                     @RequestBody(required = false) Map<String, String> body) {
        String worker = workerId(body);
        Optional<AgentTask> claimed = agentTaskService.claim(id, worker);
        return claimed
                .<Map<String, Object>>map(task -> Map.of("claimed", true, "task", task))
                .orElseGet(() -> Map.of("claimed", false));
    }

    /**
     * 文档 6.7 fencing：终态写入校验现任持有者 + 世代。
     * 接口已受 agent token 门控（AuthInterceptor），worker 为门控通道内的执行者标识；
     * 校验失败返回 409——被回收后复活的旧 worker 写不进终态。
     */
    @PostMapping("/{id}/complete")
    public ResponseEntity<AgentTask> complete(@PathVariable Long id,
                                              @RequestBody(required = false) Map<String, String> body) {
        try {
            return ResponseEntity.ok(agentTaskService.complete(
                    id, workerId(body), claimEpoch(body)));
        } catch (FencingRejectedException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
    }

    /** P1-MQ-02: 失败终态（worker 侧异常上报）——同样受 fencing 校验。 */
    @PostMapping("/{id}/fail")
    public ResponseEntity<AgentTask> fail(@PathVariable Long id,
                                          @RequestBody(required = false) Map<String, String> body) {
        try {
            return ResponseEntity.ok(agentTaskService.fail(
                    id, workerId(body), claimEpoch(body), body == null ? null : body.get("error")));
        } catch (FencingRejectedException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
    }

    /**
     * 文档 6.5：租约心跳续租。现任持有者携带 worker + claimEpoch；
     * 409 = 任务已易主 / 租约已过期 / 超出业务总时长上限——调用方应停止工作，
     * 结果无论如何都会被 fencing 层拒绝。
     */
    @PostMapping("/{id}/renew")
    public ResponseEntity<Map<String, Object>> renew(@PathVariable Long id,
                                                     @RequestBody(required = false) Map<String, String> body) {
        try {
            Instant leaseUntil = agentTaskService.renewLease(id, workerId(body), claimEpoch(body));
            return ResponseEntity.ok(Map.of("renewed", true, "leaseUntil", leaseUntil.toString()));
        } catch (FencingRejectedException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .body(Map.of("renewed", false, "reason", String.valueOf(e.getMessage())));
        }
    }

    private static String workerId(Map<String, String> body) {
        return body == null || body.get("worker") == null || body.get("worker").isBlank()
                ? "unknown-worker" : body.get("worker");
    }

    private static int claimEpoch(Map<String, String> body) {
        if (body == null || body.get("claimEpoch") == null) {
            // 未携带世代按 0 处理：与真实世代（>=1）比较必然失配 → 拒绝。
            // 升级期后的客户端必须带 epoch，这是有意的收口。
            return 0;
        }
        try {
            return Integer.parseInt(body.get("claimEpoch"));
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
