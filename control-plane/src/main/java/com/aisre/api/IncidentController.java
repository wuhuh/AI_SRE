package com.aisre.api;

import com.aisre.api.dto.DiagnosisRequest;
import com.aisre.api.dto.IncidentResponse;
import com.aisre.api.dto.IncidentTransitionRequest;
import com.aisre.api.dto.RemediationRequest;
import com.aisre.api.dto.VerificationRequest;
import com.aisre.domain.AgentStep;
import com.aisre.domain.AuditLog;
import com.aisre.domain.Evidence;
import com.aisre.domain.Incident;
import com.aisre.domain.IncidentStatus;
import com.aisre.domain.RemediationAction;
import com.aisre.domain.ToolCall;
import com.aisre.service.AgentResultService;
import com.aisre.service.AgentTaskService;
import com.aisre.service.IncidentDetailService;
import com.aisre.service.IncidentReportService;
import com.aisre.service.IncidentService;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/incidents")
public class IncidentController {

    private final IncidentService incidentService;
    private final AgentResultService agentResultService;
    private final IncidentDetailService incidentDetailService;
    private final IncidentReportService incidentReportService;

    public IncidentController(IncidentService incidentService,
                              AgentResultService agentResultService,
                              IncidentDetailService incidentDetailService,
                              IncidentReportService incidentReportService) {
        this.incidentService = incidentService;
        this.agentResultService = agentResultService;
        this.incidentDetailService = incidentDetailService;
        this.incidentReportService = incidentReportService;
    }

    /**
     * 分页列表：保持响应体仍是数组（兼容现有前端/集成测试），
     * 分页元数据走响应头：X-Total-Count / X-Page / X-Page-Size。
     * page>=0，size 收敛到 [1, 500]。
     */
    @GetMapping
    public ResponseEntity<List<IncidentResponse>> list(
            @RequestParam(required = false) IncidentStatus status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "200") int size) {
        int safePage = Math.max(0, page);
        int safeSize = Math.min(Math.max(1, size), 500);
        IncidentService.IncidentPage result = incidentService.list(status, safePage, safeSize);
        HttpHeaders headers = new HttpHeaders();
        headers.add("X-Total-Count", String.valueOf(result.total()));
        headers.add("X-Page", String.valueOf(result.page()));
        headers.add("X-Page-Size", String.valueOf(result.size()));
        return ResponseEntity.ok()
                .headers(headers)
                .body(result.items().stream().map(IncidentResponse::from).toList());
    }

    @GetMapping("/{id}")
    public IncidentResponse get(@PathVariable Long id) {
        return IncidentResponse.from(incidentService.get(id));
    }

    @PostMapping("/{id}/transition")
    public IncidentResponse transition(@PathVariable Long id,
                                       @Valid @RequestBody IncidentTransitionRequest request) {
        return IncidentResponse.from(incidentService.transition(id, request.status()));
    }

    @PostMapping("/{id}/diagnosis")
    public ResponseEntity<IncidentResponse> saveDiagnosis(@PathVariable Long id,
                                                          @Valid @RequestBody DiagnosisRequest request) {
        try {
            return ResponseEntity.ok(IncidentResponse.from(agentResultService.saveDiagnosis(id, request)));
        } catch (AgentTaskService.FencingRejectedException e) {
            // 文档 6.7：旧 worker 的诊断回写同样被栅栏拒绝——
            // 只拦 complete 而接受旧 diagnosis，旧结论仍可能触发审批/执行
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
    }

    @PostMapping("/{id}/verification")
    public IncidentResponse saveVerification(@PathVariable Long id,
                                             @Valid @RequestBody VerificationRequest request) {
        return IncidentResponse.from(agentResultService.saveVerification(id, request));
    }

    @PostMapping("/{id}/remediations")
    public RemediationAction createRemediation(@PathVariable Long id,
                                               @Valid @RequestBody RemediationRequest request) {
        return agentResultService.createRemediation(id, request);
    }

    @GetMapping("/{id}/evidence")
    public List<Evidence> evidence(@PathVariable Long id) {
        return incidentDetailService.evidence(id);
    }

    @GetMapping("/{id}/tool-calls")
    public List<ToolCall> toolCalls(@PathVariable Long id) {
        return incidentDetailService.toolCalls(id);
    }

    @GetMapping("/{id}/steps")
    public List<AgentStep> steps(@PathVariable Long id) {
        return incidentDetailService.steps(id);
    }

    @GetMapping("/{id}/remediations")
    public List<RemediationAction> remediations(@PathVariable Long id) {
        return incidentDetailService.remediations(id);
    }

    @GetMapping("/{id}/audit-logs")
    public List<AuditLog> auditLogs(@PathVariable Long id) {
        return incidentDetailService.auditLogs(id);
    }

    @GetMapping("/{id}/report")
    public java.util.Map<String, Object> report(@PathVariable Long id) {
        return incidentReportService.generate(id);
    }
}