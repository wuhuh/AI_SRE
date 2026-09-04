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
import com.aisre.service.IncidentDetailService;
import com.aisre.service.IncidentReportService;
import com.aisre.service.IncidentService;
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

    @GetMapping
    public List<IncidentResponse> list(@RequestParam(required = false) IncidentStatus status) {
        return incidentService.list(status).stream().map(IncidentResponse::from).toList();
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
    public IncidentResponse saveDiagnosis(@PathVariable Long id,
                                          @Valid @RequestBody DiagnosisRequest request) {
        return IncidentResponse.from(agentResultService.saveDiagnosis(id, request));
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