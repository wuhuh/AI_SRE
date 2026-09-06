package com.aisre.api;

import com.aisre.api.dto.ApprovalCreateRequest;
import com.aisre.api.dto.ApprovalRequest;
import com.aisre.domain.Approval;
import com.aisre.security.AuthService;
import com.aisre.service.ApprovalService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/approvals")
public class ApprovalController {

    private final ApprovalService approvalService;
    private final AuthService authService;

    public ApprovalController(ApprovalService approvalService, AuthService authService) {
        this.approvalService = approvalService;
        this.authService = authService;
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
    public Approval decide(@PathVariable Long id, @RequestBody ApprovalRequest request,
                           HttpServletRequest httpRequest) {
        // P1-CP-12: decidedBy 取 JWT sub（operator 未显式给时），不再落 unknown
        String operator = request.operator();
        if (operator == null || operator.isBlank()) {
            operator = jwtSubject(httpRequest);
        }
        ApprovalRequest resolved = new ApprovalRequest(request.decision(), operator,
                request.comment(), request.context());
        return approvalService.decide(id, resolved);
    }

    private String jwtSubject(HttpServletRequest request) {
        String auth = request.getHeader("Authorization");
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                Map<String, String> claims = authService.parse(auth.substring(7));
                String sub = claims.get("username");
                if (sub != null && !sub.isBlank()) {
                    return sub;
                }
            } catch (Exception ignored) {
                // 已过 AuthInterceptor 校验，解析失败仅退回 unknown-operator
            }
        }
        return "unknown-operator";
    }
}
