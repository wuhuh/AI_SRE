package com.aisre.api;

import com.aisre.api.dto.ApprovalCreateRequest;
import com.aisre.api.dto.ApprovalRequest;
import com.aisre.domain.Approval;
import com.aisre.service.ApprovalService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/approvals")
public class ApprovalController {

    private final ApprovalService approvalService;

    public ApprovalController(ApprovalService approvalService) {
        this.approvalService = approvalService;
    }

    @GetMapping("/incident/{incidentId}")
    public List<Approval> listByIncident(@PathVariable Long incidentId) {
        return approvalService.listByIncident(incidentId);
    }

    @PostMapping
    public Approval create(@RequestBody ApprovalCreateRequest request) {
        return approvalService.create(
                request.incidentId(),
                request.actionType(),
                request.actionPayload(),
                request.requestedBy() != null ? request.requestedBy() : "agent"
        );
    }

    @PostMapping("/{id}/decision")
    public Approval decide(@PathVariable Long id, @RequestBody ApprovalRequest request) {
        return approvalService.decide(id, request);
    }
}