package com.aisre.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * 认证拦截器：
 * - 用户写操作（审批/状态推进）：JWT（ADMIN/OPERATOR）；
 * - Agent 回调（诊断/验证/修复结果上报、任务领取/完成/失败）：静态 X-Agent-Token。
 * Agent token 为空 = fail-closed（回调一律拒绝），部署必须显式配置。
 */
@Component
public class AuthInterceptor implements HandlerInterceptor {

    private static final org.slf4j.Logger log =
            org.slf4j.LoggerFactory.getLogger(AuthInterceptor.class);

    private final AuthService authService;
    private final String agentToken;
    private final String webhookSecret;
    private volatile boolean webhookWarned = false;

    public AuthInterceptor(AuthService authService,
                           @Value("${aisre.agent.token:}") String agentToken,
                           @Value("${aisre.webhook.secret:}") String webhookSecret) {
        this.authService = authService;
        this.agentToken = agentToken == null ? "" : agentToken.trim();
        this.webhookSecret = webhookSecret == null ? "" : webhookSecret.trim();
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();
        String method = request.getMethod();

        if (path.equals("/api/v1/auth/login") || path.startsWith("/api/v1/stream")) {
            return true;
        }

        // P1-CP-14: webhooks 也需要鉴权——共享 secret（X-Webhook-Token，常量时间比较）。
        boolean webhook = path.startsWith("/api/v1/alerts") && !"GET".equals(method);
        if (webhook) {
            return requireWebhookToken(request, response);
        }

        // Agent callbacks authenticate with the shared static token, not a user JWT.
        boolean agentCallback = path.matches(".*/incidents/\\d+/(diagnosis|verification|remediations)")
                || path.startsWith("/api/v1/tasks/");
        if (agentCallback) {
            return requireAgentToken(request, response);
        }

        // P1-CP-14: 读接口 ≥VIEWER——Bearer JWT（任意角色）或有效 agent token 皆可。
        // 流式接口（SSE，EventSource 无法带头）单独放行；前端登录后带 token。
        if ("GET".equals(method) && path.startsWith("/api/v1/")) {
            return requireReadAccess(request, response);
        }

        // User-facing write operations require ADMIN or OPERATOR.
        boolean protectedWrite = path.startsWith("/api/v1/approvals")
                || path.matches(".*/incidents/\\d+/transition");
        if (!protectedWrite) {
            return true;
        }

        String auth = request.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "missing or invalid token");
        }
        try {
            java.util.Map<String, String> claims = authService.parse(auth.substring(7));
            String role = claims.get("role");
            if (!"ADMIN".equals(role) && !"OPERATOR".equals(role)) {
                return reject(response, HttpServletResponse.SC_FORBIDDEN, "forbidden: insufficient role");
            }
            return true;
        } catch (Exception e) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "invalid token");
        }
    }

    private boolean requireAgentToken(HttpServletRequest request, HttpServletResponse response) throws Exception {
        if (agentToken.isEmpty()) {
            return reject(response, HttpServletResponse.SC_SERVICE_UNAVAILABLE, "agent token not configured");
        }
        String provided = request.getHeader("X-Agent-Token");
        if (provided == null || !constantTimeEquals(provided.trim(), agentToken)) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "invalid agent token");
        }
        return true;
    }

    private boolean requireWebhookToken(HttpServletRequest request, HttpServletResponse response) throws Exception {
        if (webhookSecret.isEmpty()) {
            if (!webhookWarned) {
                webhookWarned = true;
                log.warn("aisre.webhook.secret is EMPTY: alert webhooks accept unauthenticated calls (dev only)");
            }
            return true;
        }
        String provided = request.getHeader("X-Webhook-Token");
        if (provided == null || !constantTimeEquals(provided.trim(), webhookSecret)) {
            return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "invalid webhook token");
        }
        return true;
    }

    /** P1-CP-14: 读接口凭据——JWT（任意角色，含 VIEWER）或有效 agent token。 */
    private boolean requireReadAccess(HttpServletRequest request, HttpServletResponse response) throws Exception {
        String auth = request.getHeader("Authorization");
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                authService.parse(auth.substring(7));
                return true;
            } catch (Exception ignored) {
                // fallthrough to agent token
            }
        }
        // agent-runtime 只读查询单个 incident（无用户凭据）：agent token 同样放行
        if (!agentToken.isEmpty()) {
            String provided = request.getHeader("X-Agent-Token");
            if (provided != null && constantTimeEquals(provided.trim(), agentToken)) {
                return true;
            }
        }
        return reject(response, HttpServletResponse.SC_UNAUTHORIZED, "missing or invalid token");
    }

    private static boolean constantTimeEquals(String a, String b) {
        return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
    }

    private static boolean reject(HttpServletResponse response, int status, String message) throws Exception {
        response.setStatus(status);
        response.setContentType("application/json");
        response.getWriter().write("{\"error\":\"" + message + "\"}");
        return false;
    }
}
